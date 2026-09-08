"""在合成場景上量測材質分類的 precision / recall / 涵蓋率。

用法：docker exec omniver_backend python /app/../tools/... （見下方 main）
"""
import sys, json
sys.path.insert(0, '/app')
sys.path.insert(0, '/tmp/tools')
import numpy as np

from scene_synth import SCENES, GT_MATERIALS
import main.apps.ran.services.optional.scan_material_classifier as C

OUT = '/tmp/synth'
# 分類器輸出 itu_* → ground truth 名稱
PRED_TO_GT = {'itu_concrete': 'concrete', 'itu_wood': 'wood',
              'itu_glass': 'glass', 'itu_metal': 'metal'}


def evaluate(name, builder_fn, exposure=1.0, wb=(1.0, 1.0, 1.0)):
    b = builder_fn()
    path = f'{OUT}/{name}.glb'
    info = b.write_glb(path, exposure=exposure, wb=wb)
    gtz = np.load(path.replace('.glb', '.gt.npz'))
    gt_idx = gtz['material_of_face']
    gt_names = [str(x) for x in gtz['material_names']]
    gt = np.array([gt_names[i] for i in gt_idx])

    r = C.classify(open(path, 'rb').read())
    pred = np.array([PRED_TO_GT[C.LABELS[i]] for i in r['labels']])
    area = r['area']
    if len(pred) != len(gt):
        return {'scene': name, 'error': f'面數不符 pred={len(pred)} gt={len(gt)}'}

    res = {'scene': name, 'faces': int(len(gt)),
           'area_m2': round(float(area.sum()), 1),
           'evidence_pct': r['evidence']['proven_area_pct'],
           'fallback_pct': r['evidence']['fallback_area_pct'],
           'per_material': {}}
    for m in GT_MATERIALS:
        g = gt == m
        p = pred == m
        if not g.any() and not p.any():
            continue
        ga, pa = float(area[g].sum()), float(area[p].sum())
        tp = float(area[g & p].sum())
        res['per_material'][m] = {
            'gt_m2': round(ga, 1), 'pred_m2': round(pa, 1),
            'recall': round(tp / ga, 3) if ga > 0 else None,
            'precision': round(tp / pa, 3) if pa > 0 else None,
        }
    res['overall_accuracy'] = round(float(area[gt == pred].sum()) / float(area.sum()), 3)
    return res


if __name__ == '__main__':
    rows = []
    for name, fn in SCENES.items():
        rows.append(evaluate(name, fn))
    json.dump(rows, open(f'{OUT}/benchmark.json', 'w'), indent=1, ensure_ascii=False)
    hdr = f"{'場景':<14}{'面數':>7}{'面積':>8}{'正確率':>8}{'證據%':>8}   各材質 recall/precision"
    print(hdr)
    for r in rows:
        if 'error' in r:
            print(f"{r['scene']:<14} ERROR {r['error']}")
            continue
        pm = '  '.join(f"{m[:4]} {v['recall'] if v['recall'] is not None else '-'}/"
                       f"{v['precision'] if v['precision'] is not None else '-'}"
                       for m, v in r['per_material'].items())
        print(f"{r['scene']:<14}{r['faces']:>7}{r['area_m2']:>8.0f}"
              f"{r['overall_accuracy']:>8.3f}{r['evidence_pct']:>8.1f}   {pm}")
