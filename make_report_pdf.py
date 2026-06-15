"""把 report_draft.md 渲染成带学术排版的 report.html（再用 Chrome 打印成 PDF）。

用法： python make_report_pdf.py
之后： Chrome --headless --print-to-pdf 见 README / 命令。
"""
import re
import markdown

SRC = "report_draft.md"
OUT = "report.html"
SUBTITLE = ("数字经济下的市场设计 · 第一次小组作业　|　"
            "罗臻 · 李昱霖 · 由凯 · 赵子正 · 鲍荣富　|　2026")

CSS = """
@page { size: A4; margin: 17mm 18mm 18mm 18mm; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Songti SC","STSong",serif; font-size: 10.6pt; line-height: 1.62;
       color: #1b1b1b; margin: 0; }
h1 { font-family: "PingFang SC","Hiragino Sans GB",sans-serif; font-size: 19pt;
     text-align: center; margin: 0 0 3pt; line-height: 1.3; color: #0a1f3d; }
.subtitle { text-align: center; color: #5a6470; font-size: 9.3pt;
            font-family: "PingFang SC",sans-serif; margin: 0 0 16pt;
            padding-bottom: 12pt; border-bottom: 0.5px solid #c8d0d8; }
h2 { font-family: "PingFang SC","Hiragino Sans GB",sans-serif; font-size: 13pt;
     margin: 15pt 0 6pt; padding-bottom: 2.5pt; border-bottom: 1.5px solid #0a1f3d;
     color: #0a1f3d; page-break-after: avoid; }
h3 { font-family: "PingFang SC",sans-serif; font-size: 11pt; margin: 9pt 0 3pt; color:#152a4a; }
p { margin: 4.5pt 0; }
ul, ol { margin: 4.5pt 0; padding-left: 1.5em; }
li { margin: 2.5pt 0; }
strong { color: #0a1f3d; font-weight: 600; }
code { font-family: "SF Mono","Menlo",monospace; font-size: 9pt; background: #eef1f4;
       padding: 0.5px 4px; border-radius: 3px; color:#10243f; }
table { border-collapse: collapse; width: 100%; margin: 7pt 0; font-size: 9.4pt;
        page-break-inside: avoid; }
th, td { border: 0.5px solid #b8c0c8; padding: 3.5pt 7pt; text-align: left; vertical-align: top; }
th { background: #e7ecf1; font-family: "PingFang SC",sans-serif; font-weight: 600; color:#0a1f3d; }
img { display: block; max-width: 96%; margin: 9pt auto 2pt; border: 0.5px solid #d6dbe1;
      page-break-inside: avoid; }
em { color: #5a6470; font-style: normal; display: block; text-align: center;
     font-size: 8.8pt; font-family: "PingFang SC",sans-serif; margin: 0 auto 11pt; }
blockquote { background: #eef1f4; border-left: 3px solid #0a1f3d; padding: 8pt 12pt;
             color: #1f2937; margin: 8pt 0 14pt; font-size: 9.8pt; line-height: 1.56; }
blockquote p { margin: 0; }
blockquote strong { color: #0a1f3d; }
pre { background: #f4f6f8; border: 0.5px solid #d6dbe1; border-radius: 4px; padding: 7pt 9pt;
      margin: 6pt 0; font-size: 8.3pt; line-height: 1.42; white-space: pre-wrap;
      word-break: break-word; page-break-inside: avoid; color: #10243f;
      font-family: "SF Mono","Menlo",monospace; }
pre code { background: none; padding: 0; font-size: 8.3pt; color: #10243f; }
"""


def main():
    text = open(SRC, encoding="utf-8").read()
    # 去掉草稿自注释（以 "> 报告初稿" 开头那行）
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("> 报告初稿"))

    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    # 在标题后插入副标题（作者/课程/年份）
    body = re.sub(r"(</h1>)", r"\1\n<p class='subtitle'>" + SUBTITLE + "</p>", body, count=1)

    html = (f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"已生成 {OUT}（{len(html)} 字节）")


if __name__ == "__main__":
    main()
