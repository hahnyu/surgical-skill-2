"""Readable vector replacements; corrected CSV sources are retained alongside analysis."""
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


def read(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def axis(c, x, y, width, low, high, ticks, label):
    c.setStrokeColor(HexColor('#777777'))
    c.setFillColor(HexColor('#222222'))
    c.setLineWidth(.6)
    c.line(x, y, x+width, y)
    c.setFont('Helvetica', 11)
    for value in ticks:
        px = x + (value-low)/(high-low)*width
        c.line(px, y, px, y-4)
        c.drawCentredString(px, y-16, f'{value:g}')
    c.setFont('Helvetica', 11)
    c.drawCentredString(x+width/2, y-34, label)
    return lambda value: x+(value-low)/(high-low)*width


def interval(c, scale, y, low, point, high, color):
    c.setStrokeColor(HexColor(color))
    c.setFillColor(HexColor(color))
    c.setLineWidth(1.4)
    c.line(scale(low), y, scale(high), y)
    for value in [low, high]:
        c.line(scale(value), y-3, scale(value), y+3)
    c.circle(scale(point), y, 3, fill=1, stroke=0)


def build_corrected_figures(root, destination):
    out = root / 'results/corrections/2026-11-16'
    effects = read(root / 'results/locked/phase5_effect_summaries.csv')
    # Do not let the sparse ROSMA outcome compress every other task's interval.
    # Each row has an explicitly labeled local scale; no cross-task pooling.
    for number, endpoint in [(2, 'protocol_gap'), (5, 'held_task_effect_seed_average')]:
        forest = [r for r in effects if r['endpoint'] == endpoint and (
            (number == 2 and r['metric'] == 'held_minus_same_standardized_mae') or
            (number == 5 and r['candidate'] == 'I3_identity_subspace' and r['metric'] == 'standardized_mae_difference'))]
        assert len(forest) == 7
        save_csv(out / f'figure{number}_source.csv', forest)
        c = canvas.Canvas(str(destination / f'Fig{number}.pdf'), pagesize=(570, 430), invariant=1)
        c.setFont('Helvetica-Bold', 12)
        c.drawString(14, 411, 'Task-specific effects: each row has its own x-axis scale')
        for index, r in enumerate(forest):
            y = 379-index*51
            c.setFillColor(HexColor('#222222')); c.setFont('Helvetica-Bold', 11)
            c.drawString(14, y, r['dataset'])
            c.setFont('Helvetica', 11); c.drawString(14, y-14, r['task'])
            low, high, point = (float(r[k]) for k in ['ci_low', 'ci_high', 'estimate'])
            bottom, top = min(low, 0), max(high, 0)
            span = top-bottom
            bottom -= .12*span; top += .12*span
            scale = lambda v: 192+(v-bottom)/(top-bottom)*350
            c.setStrokeColor(HexColor('#aaaaaa')); c.setLineWidth(.4)
            c.line(192, y-12, 542, y-12)
            c.line(scale(0), y-15, scale(0), y+8)
            interval(c, scale, y, low, point, high, '#176b87')
            c.setFillColor(HexColor('#222222')); c.setFont('Helvetica', 11)
            for value in [bottom, 0, top]:
                c.drawCentredString(scale(value), y-26, f'{value:.2g}')
        c.setFont('Helvetica', 11)
        c.drawCentredString(367, 16, 'Held minus same standardized MAE' if number == 2 else 'Standardized MAE(I3) minus MAE(I0)')
        c.save()

    # A readable schematic replaces tiny text in the archived SVG.
    c = canvas.Canvas(str(destination / 'Fig1.pdf'), pagesize=(570, 260), invariant=1)
    boxes = [
        (10, 145, 'Cohorts', ['Four training datasets', '2,501 trials', '92 dataset-participants']),
        (200, 145, 'Representation', ['41 kinematic variables', 'Complete trials in folds', 'Training-fold transforms']),
        (390, 145, 'Evaluation', ['Same-participant folds', 'Held-out-participant folds', 'Separate fitted pipelines']),
        (390, 20, 'Interventions', ['I1-I4 and matched controls', 'Duration / projection /', 'adversarial suppression']),
        (200, 20, 'Identity diagnostics', ['Fresh linear + forest probes', 'Same-participant evaluation', 'Participant-cluster intervals']),
        (10, 20, 'Task utility', ['Seven eligible task groups', 'Paired held-out MAE', 'Native + standardized units']),
    ]
    for x, y, title, lines in boxes:
        c.setFillColor(HexColor('#f2f6f8')); c.setStrokeColor(HexColor('#176b87'))
        c.roundRect(x, y, 170, 95, 6, fill=1, stroke=1)
        c.setFillColor(HexColor('#222222')); c.setFont('Helvetica-Bold', 12)
        c.drawString(x+9, y+74, title)
        c.setFont('Helvetica', 10.5)
        for index, line in enumerate(lines):
            c.drawString(x+9, y+52-index*17, line)
    for x1, y1, x2, y2 in [(180,192,200,192),(370,192,390,192),(475,145,475,115),
                            (390,67,370,67),(200,67,180,67)]:
        c.setStrokeColor(HexColor('#555555')); c.line(x1,y1,x2,y2)
        if y1 == y2:
            direction = 1 if x2>x1 else -1
            c.line(x2,y2,x2-direction*5,y2+3); c.line(x2,y2,x2-direction*5,y2-3)
        else:
            c.line(x2,y2,x2-3,y2+5); c.line(x2,y2,x2+3,y2+5)
    c.save()

    rows = read(out / 'identity_cluster_effects.csv')
    save_csv(out / 'figure4_source.csv', rows)
    c = canvas.Canvas(str(destination / 'Fig4.pdf'), pagesize=(570, 350), invariant=1)
    scale = axis(c, 185, 60, 350, -.24, .08, [-.2, -.1, 0], 'Change in identity balanced accuracy')
    c.setStrokeColor(HexColor('#aaaaaa'))
    c.setDash(3, 3)
    c.line(scale(0), 60, scale(0), 312)
    c.setDash()
    candidates = [('I1_duration_removed', 'I1 - I0'), ('I2_duration_residualized', 'I2 - I0'),
                  ('I3_identity_subspace', 'I3 - I0'), ('random_projection', 'Random - I0'),
                  ('I4_adversarial', 'I4 - capacity'), ('I4_shuffled_identity', 'Shuffled I4 - capacity')]
    for index, (candidate, label) in enumerate(candidates):
        y = 292-index*39
        c.setFillColor(HexColor('#222222'))
        c.setFont('Helvetica', 11)
        tasks = next(r['tasks'] for r in rows if r['candidate'] == candidate)
        c.drawRightString(174, y-3, f'{label} ({tasks} tasks)')
        for model, offset, color in [('linear_probe', 5, '#176b87'), ('nonlinear_probe', -5, '#b45434')]:
            r = next(r for r in rows if r['candidate'] == candidate and r['model'] == model)
            interval(c, scale, y+offset, float(r['ci_low']), float(r['estimate']), float(r['ci_high']), color)
    for x, label, color in [(190, 'Linear probe', '#176b87'), (355, 'Nonlinear probe', '#b45434')]:
        c.setFillColor(HexColor(color)); c.circle(x, 332, 3, fill=1, stroke=0)
        c.setFont('Helvetica', 11); c.drawString(x+9, 328, label)
    c.save()

    skill = read(root / 'results/metrics/phase4_skill_performance.csv')
    effects = read(root / 'results/locked/phase5_effect_summaries.csv')
    sources = []
    c = canvas.Canvas(str(destination / 'Fig6.pdf'), pagesize=(570, 250), invariant=1)
    left = axis(c, 100, 65, 170, .6, 1, [.6, .8, 1], 'Participant-average accuracy')
    right = axis(c, 355, 65, 180, -.4, .4, [-.4, 0, .4], 'Standardized MAE difference')
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(185, 230, 'Same-participant skill')
    c.drawCentredString(445, 230, 'Held-out-participant GRS')
    c.setStrokeColor(HexColor('#aaaaaa')); c.setDash(3, 3)
    c.line(right(0), 65, right(0), 210); c.setDash()
    for task, y in [('Knot Tying', 192), ('Needle Passing', 145), ('Suturing', 98)]:
        c.setFillColor(HexColor('#222222')); c.setFont('Helvetica', 11)
        c.drawRightString(91, y-3, task)
        for candidate, offset, color in [('I0_unsuppressed', 4, '#176b87'), ('I3_identity_subspace', -4, '#b45434')]:
            r = next(r for r in skill if r['task'] == task and r['intervention'] == candidate and r['model'] == 'skill_logistic')
            value = float(r['participant_average_accuracy'])
            c.setFillColor(HexColor(color)); c.circle(left(value), y+offset, 3, fill=1, stroke=0)
            sources.append(dict(panel='same_participant_skill', task=task, candidate=candidate,
                                metric='participant_average_accuracy', estimate=value, ci_low='', ci_high=''))
        r = next(r for r in effects if r['dataset'] == 'JIGSAWS' and r['task'] == task
                 and r['endpoint'] == 'held_task_effect_seed_average' and r['candidate'] == 'I3_identity_subspace'
                 and r['metric'] == 'standardized_mae_difference')
        interval(c, right, y, float(r['ci_low']), float(r['estimate']), float(r['ci_high']), '#333333')
        sources.append(dict(panel='held_out_GRS', task=task, candidate='I3_identity_subspace',
                            metric='standardized_mae_difference', estimate=r['estimate'], ci_low=r['ci_low'], ci_high=r['ci_high']))
    c.setFont('Helvetica', 11)
    for x, label, color in [(120, 'I0', '#176b87'), (190, 'I3', '#b45434')]:
        c.setFillColor(HexColor(color)); c.circle(x, 14, 3, fill=1, stroke=0); c.drawString(x+8, 11, label)
    c.save()
    save_csv(out / 'figure6_source.csv', sources)
