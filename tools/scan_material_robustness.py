"""光度擾動測試：模擬「換一台相機/換一個場景光線」後分類結果的變化。"""
import sys, json; sys.path.insert(0,'/app')
import numpy as np
import main.apps.ran.services.optional.scan_material_classifier as C

BASE='/home/mitlab/XAPP_DT/Omnivers_platform/assets/maps/scan_20260906'
blob=open(BASE+'.glb','rb').read()
orig_load=C._load_image

def make_loader(fn):
    def loader(gltf,binary,idx):
        im=orig_load(gltf,binary,idx)
        if im is None: return None
        x=im.astype(np.float32)/255.0
        x=fn(x)
        return (np.clip(x,0,1)*255).astype(np.uint8)
    return loader

def exposure(k):  return lambda x: x*k
def gamma(g):     return lambda x: np.power(x, g)
def wb(r,b):      return lambda x: x*np.array([r,1.0,b],dtype=np.float32)
def noise(s):
    rng=np.random.default_rng(0)
    return lambda x: x + rng.normal(0,s,x.shape).astype(np.float32)

cases=[('baseline',       lambda x:x),
       ('曝光 -30%',       exposure(0.7)),
       ('曝光 +30%',       exposure(1.3)),
       ('gamma 0.8 (較亮)', gamma(0.8)),
       ('gamma 1.25 (較暗)',gamma(1.25)),
       ('白平衡偏暖 R+12%', wb(1.12,0.92)),
       ('白平衡偏冷 B+12%', wb(0.92,1.12)),
       ('雜訊 sigma 0.05',  noise(0.05))]

base=None
print('%-20s %8s %8s %8s %9s'%('情境','木頭m2','證據%','回退%','標籤改變'))
for name,fn in cases:
    C._load_image=make_loader(fn)
    r=C.classify(blob)
    lab=r['labels']; area=r['area']
    wood=float(area[lab==C.LABEL_IDX['itu_wood']].sum())
    ev=r['evidence']
    if base is None:
        base=lab.copy(); changed='—'
    else:
        ch=float(area[lab!=base].sum())/float(area.sum())
        changed='%.1f%%'%(100*ch)
    print('%-20s %7.1f %8.1f %8.1f %9s'%(name,wood,ev['proven_area_pct'],ev['fallback_area_pct'],changed))
C._load_image=orig_load
