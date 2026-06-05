import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def read_docx(path):
    out_path = path + ".txt"
    try:
        with zipfile.ZipFile(path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.XML(xml_content)
            WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            PARA = WORD_NAMESPACE + 'p'
            TEXT = WORD_NAMESPACE + 't'
            
            lines = []
            for paragraph in tree.iter(PARA):
                texts = [node.text for node in paragraph.iter(TEXT) if node.text]
                if texts:
                    lines.append(''.join(texts))
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(lines))
            print(f"Wrote to {out_path}")
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        read_docx(arg)
