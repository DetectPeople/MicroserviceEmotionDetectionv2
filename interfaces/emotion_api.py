from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, Response, abort, jsonify

from entities import Emotion, Frame, db, Person
from repository.video_repository import VideoRepository
from repository.frame_repository import FrameRepository
from use_cases.process_emotion_use_case import ProcessEmotionUseCase
from config import Config
import os
import logging
from collections import defaultdict
import statistics
import xlsxwriter
from io import BytesIO
from repository.emotion_report_repository import EmotionReportRepository   #NUEVO

emotion_api = Blueprint('emotion_api', __name__)
video_repository = VideoRepository()
frame_repository = FrameRepository()
process_emotion_use_case = ProcessEmotionUseCase()
repo = EmotionReportRepository()
@emotion_api.route('/', methods=['GET'])
def select_video():
    logging.info("Loaded video selection page.")
    videos = video_repository.get_all()
    return render_template('select_video.html', videos=videos)

@emotion_api.route('/process', methods=['POST'])
def process_video():
    video_id = int(request.form['video_id'])
    logging.info(f"Processing initiated for video ID {video_id}")
    return redirect(url_for('emotion_api.processing', video_id=video_id))

@emotion_api.route('/start_processing/<int:video_id>', methods=['GET'])
def start_processing(video_id):
    try:
        result = process_emotion_use_case.execute(video_id)
        if result is None:
            logging.info(f"Frames for video ID {video_id} are still being processed.")
            return render_template('frame_processing.html', video_id=video_id)

        output_video_filename = os.path.basename(result)
        logging.info(f"Emotion detection complete for video ID {video_id}")
        return redirect(url_for('emotion_api.result', video_filename=output_video_filename, video_id=video_id))
    except Exception as e:
        logging.error(f"Error in processing video ID {video_id}: {e}")
        return f"Error processing video: {str(e)}", 500

@emotion_api.route('/processing/<int:video_id>')
def processing(video_id):
    return render_template('processing.html', video_id=video_id)

@emotion_api.route('/result/<video_filename>/<int:video_id>')
def result(video_filename, video_id):
    rep = EmotionReportRepository().get_by_video_id(video_id)
    report_id = rep.id if rep else None

    return render_template('result.html', video_filename=video_filename, video_id=video_id, emotion_report_id = report_id)

@emotion_api.route('/videos/<video_filename>')
def get_video(video_filename):
    return send_from_directory(Config.ANNOTATED_VIDEOS_DIR, video_filename)

@emotion_api.route('/download_emotions_excel/<int:video_id>', methods=['GET'])
def download_emotions_excel(video_id):
    try:
        # Hacer una consulta directa para obtener todos los datos relevantes de Frame y Emotion para un video específico
        results = (
            db.session.query(Frame.id, Frame.frame_number, Frame.video_id, Frame.average_brightness,
                             Frame.contrast_ratio, Frame.background_complexity, Frame.color_temperature,
                             Frame.sharpness, Emotion.emotion_type, Emotion.confidence, Emotion.bbox,
                             Emotion.person_identity, Emotion.person_id)
            .join(Emotion, Frame.id == Emotion.frame_id)
            .filter(Frame.video_id == video_id)
            .all()
        )

        # Obtener las estimaciones de edad y género de todas las personas detectadas en el video
        person_info = (
            db.session.query(Person.id, Person.identity, Person.age_estimation, Person.gender_estimation)
            .join(Emotion, Person.id == Emotion.person_id)
            .join(Frame, Frame.id == Emotion.frame_id)
            .filter(Frame.video_id == video_id)
            .distinct()
            .all()
        )

        # Verificar si hay resultados
        if not results:
            logging.error(f"No data found for video ID {video_id}")
            return f"No emotion data found for video ID {video_id}", 404

        report = EmotionReportRepository().get_by_video_id(video_id)
        conclusion_text = report.conclusion if report and report.conclusion else "No conclusion has been recorded."
        # Crear un archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Emotion Data')

        # Escribir el encabezado del Excel, incluyendo las nuevas columnas
        headers = ['Frame ID', 'Frame Number in Video', 'Video ID', 'Average Brightness', 'Contrast Ratio',
                   'Background Complexity', 'Color Temperature', 'Sharpness', 'Detected Emotion',
                   'Confidence Level (%)', 'Bounding Box Coordinates', 'Person Identity', 'Person ID']
        worksheet.write_row('A1', headers)

        # Variables para métricas
        total_confidence = []
        emotion_count = defaultdict(int)
        person_emotion_count = defaultdict(int)  # Contador de emociones por persona

        # Listas para calcular los promedios de las métricas de frame
        brightness_values = []
        contrast_values = []
        complexity_values = []
        temperature_values = []
        sharpness_values = []

        # Escribir los datos en el Excel y acumular métricas
        row_index = 1
        for row in results:
            (frame_id, frame_number, video_id, average_brightness, contrast_ratio, background_complexity,
             color_temperature, sharpness, emotion_type, confidence, bbox, person_identity, person_id) = row

            # Guardar la información en la hoja de Excel
            worksheet.write_row(row_index, 0, [
                frame_id,  # Frame ID
                frame_number,  # Frame Number
                video_id,  # Video ID
                average_brightness if average_brightness is not None else 'N/A',  # Average Brightness
                contrast_ratio if contrast_ratio is not None else 'N/A',  # Contrast Ratio
                background_complexity if background_complexity is not None else 'N/A',  # Background Complexity
                color_temperature if color_temperature is not None else 'N/A',  # Color Temperature
                sharpness if sharpness is not None else 'N/A',  # Sharpness
                emotion_type,  # Detected Emotion
                round(confidence * 100, 2),  # Confidence Level as Percentage
                bbox,  # Bounding Box
                person_identity if person_identity else 'Unknown',  # Person Identity
                person_id  # Person ID
            ])

            # Acumular datos para métricas
            if average_brightness is not None:
                brightness_values.append(average_brightness)
            if contrast_ratio is not None:
                contrast_values.append(contrast_ratio)
            if background_complexity is not None:
                complexity_values.append(background_complexity)
            if color_temperature is not None:
                temperature_values.append(color_temperature)
            if sharpness is not None:
                sharpness_values.append(sharpness)
            total_confidence.append(confidence)
            emotion_count[emotion_type] += 1
            person_emotion_count[person_id] += 1
            row_index += 1

        # Calcular promedios de las métricas de frame
        avg_brightness = round(statistics.mean(brightness_values), 2) if brightness_values else 0
        avg_contrast = round(statistics.mean(contrast_values), 2) if contrast_values else 0
        avg_complexity = round(statistics.mean(complexity_values), 2) if complexity_values else 0
        avg_temperature = round(statistics.mean(temperature_values), 2) if temperature_values else 0
        avg_sharpness = round(statistics.mean(sharpness_values), 2) if sharpness_values else 0

        # Calcular métricas de emociones
        avg_confidence = round(statistics.mean(total_confidence) * 100, 2) if total_confidence else 0
        most_common_emotion = max(emotion_count, key=emotion_count.get) if emotion_count else "None"
        avg_emotions_per_person = round(sum(person_emotion_count.values()) / len(person_emotion_count),
                                        2) if person_emotion_count else 0

        # Escribir resumen de métricas
        summary_start_row = row_index + 2
        worksheet.write(summary_start_row, 0, 'Summary:')
        worksheet.write(summary_start_row + 1, 0, 'Total Frames Analyzed')
        worksheet.write(summary_start_row + 1, 1, len(set([row[0] for row in results])))
        worksheet.write(summary_start_row + 2, 0, 'Total Emotions Detected')
        worksheet.write(summary_start_row + 2, 1, len(results))
        worksheet.write(summary_start_row + 3, 0, 'Average Confidence Level (%)')
        worksheet.write(summary_start_row + 3, 1, avg_confidence)
        worksheet.write(summary_start_row + 4, 0, 'Most Common Emotion Detected')
        worksheet.write(summary_start_row + 4, 1, most_common_emotion)
        worksheet.write(summary_start_row + 5, 0, 'Average Number of Emotions per Person')
        worksheet.write(summary_start_row + 5, 1, avg_emotions_per_person)

        # Escribir información de todas las personas detectadas
        person_info_start_row = summary_start_row + 14
        worksheet.write(person_info_start_row, 0, 'Detected Persons:')
        worksheet.write_row(person_info_start_row + 1, 0, ['Person ID', 'Identity', 'Age Estimation', 'Gender Estimation'])

        # Escribir cada persona detectada en el Excel
        for index, person in enumerate(person_info):
            worksheet.write_row(person_info_start_row + 2 + index, 0, [
                person.id,  # Person ID
                person.identity if person.identity else 'Unknown',  # Identity
                person.age_estimation if person.age_estimation else 'Unknown',  # Age Estimation
                person.gender_estimation if person.gender_estimation else 'Unknown'  # Gender Estimation
            ])

        # Crear gráficos para visualización

        # 1. Gráfico de Frecuencia de Emociones
        emotion_chart = workbook.add_chart({'type': 'column'})
        emotion_names = list(emotion_count.keys())
        emotion_values = list(emotion_count.values())

        # Escribir los nombres de emociones y sus frecuencias para el gráfico
        chart_data_row = person_info_start_row + len(person_info) + 4
        worksheet.write_row(chart_data_row, 0, ['Emotion', 'Frequency'])
        for i, (emotion, count) in enumerate(emotion_count.items()):
            worksheet.write(chart_data_row + i + 1, 0, emotion)
            worksheet.write(chart_data_row + i + 1, 1, count)

        # Configurar datos del gráfico de emociones
        emotion_chart.add_series({
            'categories': f'={worksheet.name}!$A${chart_data_row + 2}:$A${chart_data_row + len(emotion_count) + 1}',
            'values': f'={worksheet.name}!$B${chart_data_row + 2}:$B${chart_data_row + len(emotion_count) + 1}',
            'name': 'Emotion Frequency'
        })

        emotion_chart.set_title({'name': 'Emotion Frequency Analysis'})
        emotion_chart.set_x_axis({'name': 'Emotion'})
        emotion_chart.set_y_axis({'name': 'Frequency'})
        emotion_chart.set_style(11)

        # Insertar el gráfico de emociones en la hoja de Excel
        worksheet.insert_chart(f'D{chart_data_row}', emotion_chart)


        # 2. Gráfico de promedios de las métricas de frame
        avg_chart = workbook.add_chart({'type': 'bar'})
        metric_names = ['Average Brightness', 'Contrast Ratio', 'Background Complexity', 'Color Temperature', 'Sharpness']
        metric_values = [avg_brightness, avg_contrast, avg_complexity, avg_temperature, avg_sharpness]

        # Escribir nombres de métricas y sus promedios para el gráfico
        metric_chart_data_row = chart_data_row + len(emotion_count) + 6
        worksheet.write_row(metric_chart_data_row, 0, ['Metric', 'Average Value'])
        for i, (metric, value) in enumerate(zip(metric_names, metric_values)):
            worksheet.write(metric_chart_data_row + i + 1, 0, metric)
            worksheet.write(metric_chart_data_row + i + 1, 1, value)

        # Configurar datos del gráfico de métricas
        avg_chart.add_series({
            'categories': f'={worksheet.name}!$A${metric_chart_data_row + 2}:$A${metric_chart_data_row + len(metric_names) + 1}',
            'values': f'={worksheet.name}!$B${metric_chart_data_row + 2}:$B${metric_chart_data_row + len(metric_names) + 1}',
            'name': 'Average Metrics'
        })

        avg_chart.set_title({'name': 'Frame Metrics Analysis'})
        avg_chart.set_x_axis({'name': 'Metric'})
        avg_chart.set_y_axis({'name': 'Average Value'})
        avg_chart.set_style(11)

        # Insertar el gráfico de métricas en la hoja de Excel
        worksheet.insert_chart(f'D{metric_chart_data_row}', avg_chart)

        # Calcular fila final luego del último gráfico (gráfico de métricas)
        last_graph_row = metric_chart_data_row + len(metric_names) + 10  # espacio después del gráfico

        # Crear formato visual para la conclusión
        highlight_format = workbook.add_format({
            'bold': True,
            'bg_color': '#DDEBF7',  # Azul claro
            'border': 1,
            'text_wrap': True,
            'valign': 'top'
        })

        # Escribir conclusión dejando espacio suficiente debajo del gráfico
        conclusion_start_row = last_graph_row + 4
        worksheet.write(conclusion_start_row, 0, 'Conclusion:', highlight_format)
        worksheet.write(conclusion_start_row + 1, 0, conclusion_text, highlight_format)

        # Ajustar formato visual
        worksheet.set_row(conclusion_start_row + 1, 80)
        worksheet.set_column('A:B', 60)
        worksheet.set_selection(f'A{conclusion_start_row + 1}')

        # Cerrar y devolver el archivo Excel
        workbook.close()
        output.seek(0)

        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": f"attachment;filename=emotion_data_report_for_video_{video_id}.xlsx"}
        )

    except Exception as e:
        logging.error(f"Error generating Excel for video ID {video_id}: {str(e)}")
        return f"Error generating Excel for video ID {video_id}: {str(e)}", 500

@emotion_api.route('/view_charts/<int:video_id>', methods=['GET'])
def view_charts(video_id):
    # Cargar emociones y métricas por frame
    results = (
        db.session.query(Frame, Emotion, Person)  # Suponiendo que tienes una relación con la tabla Person
        .join(Emotion, Frame.id == Emotion.frame_id)
        .join(Person, Emotion.person_id == Person.id)
        # Relación con Person (ajustar según tu modelo)
        .filter(Frame.video_id == video_id)
        .all()
    )

    emotion_count = defaultdict(int)
    brightness = []
    contrast = []
    complexity = []
    temperature = []
    sharpness = []
    emotions_by_person = defaultdict(lambda: defaultdict(int))  # Para almacenar emociones por persona

    for frame, emotion, person in results:
        emotion_count[emotion.emotion_type] += 1
        person_key = person.identity or f"Person {person.id}"
        emotions_by_person[person_key][emotion.emotion_type] += 1

        if frame.average_brightness is not None:
            brightness.append(frame.average_brightness)
        if frame.contrast_ratio is not None:
            contrast.append(frame.contrast_ratio)
        if frame.background_complexity is not None:
            complexity.append(frame.background_complexity)
        if frame.color_temperature is not None:
            temperature.append(frame.color_temperature)
        if frame.sharpness is not None:
            sharpness.append(frame.sharpness)

    # Métricas promediadas
    metrics = {
        'Average Brightness': round(statistics.mean(brightness), 2) if brightness else 0,
        'Contrast Ratio': round(statistics.mean(contrast), 2) if contrast else 0,
        'Background Complexity': round(statistics.mean(complexity), 2) if complexity else 0,
        'Color Temperature': round(statistics.mean(temperature), 2) if temperature else 0,
        'Sharpness': round(statistics.mean(sharpness), 2) if sharpness else 0,
    }

    # Obtener edades por persona (si están disponibles)
    person_info = {}
    age_promedios = []

    for _, _, person in results:
        person_key = person.identity or f"Person {person.id}"

        if person_key not in person_info:
            # Convertir el rango de edad a promedio estimado (ej. "(38-43)" → 40.5)
            if person.age_estimation:
                age_str = person.age_estimation.replace('(', '').replace(')', '')
                age_range = list(map(int, age_str.split('-')))
                average_age = sum(age_range) / 2
                age_promedios.append(average_age)
            else:
                average_age = None

            person_info[person_key] = {
                'age_estimation': person.age_estimation,
                'gender': person.gender_estimation,
                'avg_age_value': average_age
            }

    # Promedio general de edad
    general_avg_age = round(statistics.mean(age_promedios), 2) if age_promedios else None

    # Contador de géneros
    gender_distribution = defaultdict(int)
    # Contador de géneros con limpieza y estandarización
    for p in person_info.values():
        if p['gender']:
            gender = p['gender'].strip().capitalize()  # " male  " → "Male"
            gender_distribution[gender] += 1

    #print("Person ages:", person_ages)
    person_ages = {k: v['avg_age_value'] for k, v in person_info.items() if v['avg_age_value'] is not None}

    rep = EmotionReportRepository().get_by_video_id(video_id)
    report_id = rep.id if rep else None  # ② valor a pasar

    return render_template('charts.html',
                           emotion_data=dict(emotion_count),
                           emotions_by_person=emotions_by_person,
                           metrics=metrics,
                           person_info=person_info,
                           general_avg_age=general_avg_age,
                           gender_distribution=dict(gender_distribution),
                           video_id=video_id,
                           person_ages=person_ages,
                           emotion_report_id=report_id)


##nuevo
@emotion_api.get('/api/reports/<int:report_id>/conclusion')
def get_conclusion(report_id):
    report = repo.get_by_id(report_id)
    if not report:
        abort(404, description="Report not found")
    return jsonify({
        'report_id': report.id,
        'conclusion': report.conclusion or ""
    })

# --- Crear/Actualizar conclusión ---
@emotion_api.post('/api/reports/<int:report_id>/conclusion')
def set_conclusion(report_id):
    report = repo.get_by_id(report_id)
    if not report:
        abort(404, description="Report not found")
    data = request.get_json(force=True)
    text = data.get('conclusion', '').strip()
    if text == '':
        abort(400, description="Conclusion cannot be empty")
    updated = repo.update_conclusion(report_id, text)
    return jsonify({'status': 'ok', 'report_id': updated.id, 'conclusion': updated.conclusion})

@emotion_api.delete('/api/reports/<int:report_id>/conclusion')
def delete_conclusion(report_id):
    report = repo.get_by_id(report_id)
    if not report:
        abort(404, description="Report not found")
    cleared = repo.clear_conclusion(report_id)
    return jsonify({
        'status': 'deleted',
        'report_id': cleared.id,
        'conclusion': cleared.conclusion
    })

@emotion_api.patch('/api/reports/<int:report_id>/conclusion')
def patch_conclusion(report_id):
    report = repo.get_by_id(report_id)
    if not report:
        abort(404, description="Report not found")
    data = request.get_json(force=True)
    text = data.get('conclusion', '').strip()
    if text == '':
        abort(400, description="Conclusion cannot be empty")
    updated = repo.update_conclusion(report_id, text)
    return jsonify({'status': 'updated', 'report_id': updated.id, 'conclusion': updated.conclusion})
