"""Predeclared nominal slider-height sensitivity; never policy calibration."""
import hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.record_wuji_robust_goal import R,D,record


def main():
    source=R/'assets/objects/knife_wuji_real_size_20261002/000';records=[]
    for name,offset in [('sensitivity-height-minus1',-.001),('sensitivity-height-plus1',.001)]:
        dest=R/'assets/objects/knife_wuji_dense_under_20261003'/name
        assert not dest.exists(), dest
        shutil.copytree(source,dest)
        urdf=dest/'mobility.urdf';tree=ET.parse(urdf);origin=tree.find("./joint[@name='slider']/origin");xyz=[float(x) for x in origin.get('xyz').split()];xyz[1]+=offset;origin.set('xyz',' '.join(map(str,xyz)));tree.write(urdf,encoding='utf-8',xml_declaration=True)
        p=dest/'parameters.json';j=json.loads(p.read_text());j.update(id=name,split='sensitivity',slider_height_offset_m=offset,source_nominal_urdf_sha256=hashlib.sha256((source/'mobility.urdf').read_bytes()).hexdigest(),urdf_sha256=hashlib.sha256(urdf.read_bytes()).hexdigest(),scope='Nominal135x16x12body/slidergeometry/mass/inertia/travel unchanged. Physicalsliderjointheightoffsetonly; actor retainsoriginalnominalgeometry/oncecalibration. Not real tolerance or calibration.')
        j['slider_origin'][1]+=offset;j['slider_initial_center'][1]+=offset;p.write_text(json.dumps(j,indent=2));records.append(dict(instance=name,offset_m=offset,path=str(dest.relative_to(R)),urdf_sha256=j['urdf_sha256']))
    out=D/'height-sensitivity-assets-v1.json';out.write_text(json.dumps(dict(records=records,scope='Predeclaredseparatesensitivity; independent012-015notread'),indent=2));record('height_sensitivity_assets_prepared',evidence=str(out.relative_to(R)),config=records,conclusion='Onlyphysicalsliderheightchangedby±1mm; policypriorunchanged. No heldoutparametersread.',next='Samefrozencandidate32actualTABLEcases aftermaincandidatefreeze')


if __name__=='__main__':main()
