import tempfile
import unittest
from pathlib import Path
import fitz
from redpen import render_redpen, check_minutes

class RenderingTests(unittest.TestCase):
    def test_pages_rotation_and_pending(self):
        for rotation in (0,90,180,270):
            with self.subTest(rotation=rotation), tempfile.TemporaryDirectory() as tmp:
                tmp=Path(tmp); src=tmp/'source.pdf'; dst=tmp/'out.pdf'
                d=fitz.open(); p=d.new_page(width=400,height=600)
                p.insert_text((60,150),'original text'); p.set_rotation(rotation); d.save(src); d.close()
                data={'version':1,'corrections':[{'page':1,'bbox':[.15,.25,.35,.30], 'replacement':'確認', 'confidence':.99}, {'page':1,'bbox':None,'comment':'保留','confidence':.2}]}
                report=render_redpen(src,data,dst,tmp/'preview')
                self.assertEqual(len(report['placed']),1); self.assertEqual(len(report['pending']),1)
                with fitz.open(src) as original, fitz.open(dst) as out:
                    self.assertEqual(len(out),len(original)); self.assertEqual(out[0].rect,original[0].rect)
                    self.assertEqual(out[0].rotation,rotation)
                    self.assertIn('確認',out[0].get_text())
                    self.assertIn('original text',out[0].get_text())
                self.assertTrue((tmp/'preview/page-001.png').exists())
                with self.assertRaises(FileExistsError): render_redpen(src,data,dst)
                with self.assertRaises(ValueError): render_redpen(src,data,src)
    def test_dense_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); d=fitz.open(); p=d.new_page(width=200,height=200)
            p.draw_rect(p.rect,fill=(0,0,0)); d.save(tmp/'a.pdf'); d.close()
            r=render_redpen(tmp/'a.pdf',{'version':1,'corrections':[{'page':1,'bbox':[.1,.1,.2,.2],'replacement':'修正','confidence':1}]},tmp/'b.pdf')
            self.assertEqual(len(r['pending']),1); self.assertEqual(len(r['placed']),0)
    def test_many_comments_do_not_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); d=fitz.open(); d.new_page(); d.save(tmp/'a.pdf'); d.close()
            items=[{'page':1,'bbox':[.2,.1+n*.08,.4,.13+n*.08],'replacement':'要確認','confidence':1} for n in range(9)]
            report=render_redpen(tmp/'a.pdf',{'version':1,'corrections':items},tmp/'b.pdf')
            self.assertEqual(len(report['placed']),9)
            boxes=[fitz.Rect(x['label_bbox']) for x in report['placed']]
            for i,box in enumerate(boxes):
                self.assertTrue(all(not box.intersects(other) for other in boxes[i+1:]))
    def test_time(self):
        self.assertEqual(check_minutes('08:30','17:00',[('12:00','13:00')])['minutes'],450)
        self.assertEqual(check_minutes('08:30','16:59',[('12:00','13:00')])['status'],'不足')
        self.assertEqual(check_minutes('08:30','17:00')['status'],'要確認')
        self.assertEqual(check_minutes('08:30','17:00',[('12:00','13:00'),('12:30','14:00')])['status'],'要確認')

if __name__=='__main__': unittest.main()
