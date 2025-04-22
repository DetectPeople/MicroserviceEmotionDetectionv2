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
        include_summary = request.args.get('summary', 'true') == 'true'
        include_data = request.args.get('data', 'true') == 'true'
        include_chart = request.args.get('chart', 'true') == 'true'
        include_gender = request.args.get('gender', 'true') == 'true'
        include_conclusion = request.args.get('conclusion', 'true') == 'true'

        results = (
            db.session.query(Frame.id, Frame.frame_number, Frame.video_id, Frame.average_brightness,
                             Frame.contrast_ratio, Frame.background_complexity, Frame.color_temperature,
                             Frame.sharpness, Emotion.emotion_type, Emotion.confidence, Emotion.bbox,
                             Emotion.person_identity, Emotion.person_id)
            .join(Emotion, Frame.id == Emotion.frame_id)
            .filter(Frame.video_id == video_id)
            .all()
        )

        person_info = (
            db.session.query(Person.id, Person.identity, Person.age_estimation, Person.gender_estimation)
            .join(Emotion, Person.id == Emotion.person_id)
            .join(Frame, Frame.id == Emotion.frame_id)
            .filter(Frame.video_id == video_id)
            .distinct()
            .all()
        )

        if not results:
            return "No emotion data found", 404

        report = EmotionReportRepository().get_by_video_id(video_id)
        conclusion_text = report.conclusion if report and report.conclusion else "No conclusion has been recorded."

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Emotion Data")
        current_row = 0

        if include_data:
            headers = ['Frame ID', 'Frame Number', 'Video ID', 'Average Brightness', 'Contrast Ratio',
                       'Background Complexity', 'Color Temperature', 'Sharpness', 'Detected Emotion',
                       'Confidence (%)', 'Bounding Box', 'Person Identity', 'Person ID']
            worksheet.write_row(current_row, 0, headers)
            current_row += 1

        total_confidence = []
        brightness_values, contrast_values = [], []
        complexity_values, temperature_values, sharpness_values = [], [], []
        emotion_count = defaultdict(int)
        person_emotion_count = defaultdict(int)

        for row in results:
            (frame_id, frame_num, v_id, bright, contrast, complexi, temp, sharp, emo, conf, bbox, ident, pid) = row

            if include_data:
                worksheet.write_row(current_row, 0, [
                    frame_id, frame_num, v_id,
                    bright if bright is not None else 'N/A',
                    contrast if contrast is not None else 'N/A',
                    complexi if complexi is not None else 'N/A',
                    temp if temp is not None else 'N/A',
                    sharp if sharp is not None else 'N/A',
                    emo, round(conf * 100, 2), bbox,
                    ident if ident else 'Unknown', pid
                ])
                current_row += 1

            if bright is not None: brightness_values.append(bright)
            if contrast is not None: contrast_values.append(contrast)
            if complexi is not None: complexity_values.append(complexi)
            if temp is not None: temperature_values.append(temp)
            if sharp is not None: sharpness_values.append(sharp)
            total_confidence.append(conf)
            emotion_count[emo] += 1
            person_emotion_count[pid] += 1

        avg_brightness = round(statistics.mean(brightness_values), 2) if brightness_values else 0
        avg_contrast = round(statistics.mean(contrast_values), 2) if contrast_values else 0
        avg_complexity = round(statistics.mean(complexity_values), 2) if complexity_values else 0
        avg_temperature = round(statistics.mean(temperature_values), 2) if temperature_values else 0
        avg_sharpness = round(statistics.mean(sharpness_values), 2) if sharpness_values else 0
        avg_confidence = round(statistics.mean(total_confidence) * 100, 2) if total_confidence else 0
        most_common_emotion = max(emotion_count, key=emotion_count.get) if emotion_count else "None"
        avg_emotions_per_person = round(sum(person_emotion_count.values()) / len(person_emotion_count), 2) if person_emotion_count else 0

        if include_summary:
            current_row += 2
            worksheet.write(current_row, 0, "Summary:")
            worksheet.write(current_row + 1, 0, "Total Frames Analyzed")
            worksheet.write(current_row + 1, 1, len(set([r[0] for r in results])))
            worksheet.write(current_row + 2, 0, "Total Emotions Detected")
            worksheet.write(current_row + 2, 1, len(results))
            worksheet.write(current_row + 3, 0, "Average Confidence Level (%)")
            worksheet.write(current_row + 3, 1, avg_confidence)
            worksheet.write(current_row + 4, 0, "Most Common Emotion")
            worksheet.write(current_row + 4, 1, most_common_emotion)
            worksheet.write(current_row + 5, 0, "Average Emotions per Person")
            worksheet.write(current_row + 5, 1, avg_emotions_per_person)
            current_row += 7

        if person_info:
            worksheet.write(current_row, 0, "Detected Persons:")
            worksheet.write_row(current_row + 1, 0, ['Person ID', 'Identity', 'Age Estimation', 'Gender Estimation'])
            for i, p in enumerate(person_info):
                worksheet.write_row(current_row + 2 + i, 0, [
                    p.id, p.identity or 'Unknown', p.age_estimation or 'Unknown', p.gender_estimation or 'Unknown'
                ])
            current_row += 2 + len(person_info) + 2

        if include_chart:
            worksheet.write_row(current_row, 0, ['Emotion', 'Frequency'])
            for i, (emo, count) in enumerate(emotion_count.items()):
                worksheet.write(current_row + i + 1, 0, emo)
                worksheet.write(current_row + i + 1, 1, count)
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'categories': f"='Emotion Data'!$A${current_row + 2}:$A${current_row + 1 + len(emotion_count)}",
                'values': f"='Emotion Data'!$B${current_row + 2}:$B${current_row + 1 + len(emotion_count)}",
                'name': 'Emotion Frequency'
            })
            chart.set_title({'name': 'Emotion Frequency Analysis'})
            chart.set_x_axis({'name': 'Emotion'})
            chart.set_y_axis({'name': 'Frequency'})
            worksheet.insert_chart(f'D{current_row}', chart)
            current_row += len(emotion_count) + 8

            worksheet.write_row(current_row, 0, ['Metric', 'Average Value'])
            metrics = ['Average Brightness', 'Contrast Ratio', 'Background Complexity', 'Color Temperature', 'Sharpness']
            values = [avg_brightness, avg_contrast, avg_complexity, avg_temperature, avg_sharpness]
            for i, (m, v) in enumerate(zip(metrics, values)):
                worksheet.write(current_row + i + 1, 0, m)
                worksheet.write(current_row + i + 1, 1, v)
            chart2 = workbook.add_chart({'type': 'bar'})
            chart2.add_series({
                'categories': f"='Emotion Data'!$A${current_row + 2}:$A${current_row + 1 + len(metrics)}",
                'values': f"='Emotion Data'!$B${current_row + 2}:$B${current_row + 1 + len(metrics)}",
                'name': 'Average Metrics'
            })
            chart2.set_title({'name': 'Frame Metrics Analysis'})
            chart2.set_x_axis({'name': 'Metric'})
            chart2.set_y_axis({'name': 'Average Value'})
            worksheet.insert_chart(f'D{current_row}', chart2)
            current_row += len(metrics) + 8

        if include_gender and person_info:
            gender_count = defaultdict(int)
            for p in person_info:
                gender = p.gender_estimation or "Unknown"
                gender_count[gender] += 1

            gender_chart_start_row = current_row
            worksheet.write_row(gender_chart_start_row, 0, ['Gender', 'Count'])

            for i, (gender, count) in enumerate(gender_count.items()):
                worksheet.write(gender_chart_start_row + i + 1, 0, gender)
                worksheet.write(gender_chart_start_row + i + 1, 1, count)

            pie_chart = workbook.add_chart({'type': 'pie'})
            pie_chart.add_series({
                'name': 'Gender Distribution',
                'categories': f"='Emotion Data'!$A${gender_chart_start_row + 2}:$A${gender_chart_start_row + 1 + len(gender_count)}",
                'values': f"='Emotion Data'!$B${gender_chart_start_row + 2}:$B${gender_chart_start_row + 1 + len(gender_count)}"
            })
            pie_chart.set_title({'name': 'Gender Distribution'})
            pie_chart.set_style(10)

            worksheet.insert_chart(f'D{gender_chart_start_row}', pie_chart)
            current_row = gender_chart_start_row + len(gender_count) + 8

        if include_conclusion:
            worksheet.write(current_row, 0, "Conclusion:")
            worksheet.write(current_row + 1, 0, conclusion_text)
            worksheet.set_row(current_row + 1, 80)
            worksheet.set_column('A:B', 60)

        workbook.close()
        output.seek(0)
        return Response(output,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={"Content-Disposition": f"attachment;filename=emotion_data_report_for_video_{video_id}.xlsx"})
    except Exception as e:
        logging.error(f"Excel generation failed: {str(e)}")
        return f"Error generating Excel: {str(e)}", 500


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
