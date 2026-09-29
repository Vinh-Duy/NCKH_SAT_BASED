"""Generate English presentation copies of archived LaTeX tables.

No solver calls, numerical edits, or changes to historical provenance records.
The output manifest records both original and translated file hashes.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS = {'Họ & $(h,k)$ & Mẫu & SAT OPT & ILP OPT & Có công thức': 'Family & $(h,k)$ & Cases & SAT OPT & '
                                                          'ILP OPT & Exact ref.',
 'Họ & $(h,k)$ & Bài & SAT OPT/lượt & ILP OPT/lượt & SAT đủ 3 & ILP đủ 3': 'Family & $(h,k)$ & '
                                                                           'Cases & SAT OPT runs & '
                                                                           'ILP OPT runs & SAT all '
                                                                           '3 & ILP all 3',
 'Họ & $(h,k)$ & Cặp đủ 3 OPT & SAT (s) & ILP (s)': 'Family & $(h,k)$ & Both all 3 OPT & SAT (s) & '
                                                    'ILP (s)',
 'Họ & $(h,k)$ & Mẫu & SAT biến & SAT clause & ILP biến nhị phân & ILP ràng buộc': 'Family & '
                                                                                   '$(h,k)$ & '
                                                                                   'Cases & SAT '
                                                                                   'vars & SAT '
                                                                                   'clauses & ILP '
                                                                                   'binaries & ILP '
                                                                                   'rows',
 'Gốc + thứ tự': 'Root + order',
 'Không thêm': 'None added',
 'Thứ tự': 'Order',
 'Họ & Số cặp & OPT/OPT & Chưa tối ưu & Span (OPT) & Đối xứng': 'Family & Pairs & OPT/OPT & '
                                                                'Unresolved & Span (OPT) & '
                                                                'Symmetry',
 'Họ & OPT/OPT': 'Family & OPT/OPT',
 'Trung vị': 'Median',
 'Họ & Giảm biến (\\%) & Giảm clause (\\%) & Giảm & Bằng & Tăng': 'Family & Var. reduction (\\%) & '
                                                                  'Clause reduction (\\%) & Fewer '
                                                                  '& Equal & More',
 'Họ & Xung đột B & Xung đột S & Quyết định B & Quyết định S': 'Family & Conflicts B & Conflicts S '
                                                               '& Decisions B & Decisions S',
 'Họ & Dựng CNF B & Dựng CNF S & SAT B & SAT S': 'Family & CNF build B & CNF build S & SAT B & SAT '
                                                 'S',
 'Đồ thị &': 'Graph &',
 'Span đếm': 'Count span',
 'Tập & Miền $n$ & Số cặp & Solver & Search & Budget (s)': 'Dataset & $n$ range & Pairs & Solver & '
                                                           'Search & Budget (s)',
 'Span & Trạng thái & Số mẫu': 'Span & Status & Samples',
 'Họ đồ thị & Số mẫu & OPT & Khác OPT & Span (OPT)': 'Family & Samples & OPT & Other & Span (OPT)',
 'Baseline & Symmetry & Số mẫu': 'Baseline & Symmetry & Samples'}
SOURCES = [
    *[f"paper/generated/{name}.tex" for name in
      ("coverage", "timing", "encoding", "components", "search_stats", "run_config", "unresolved")],
    "results/analysis/general_pilot_v1/summary.tex",
    "results/analysis/exact_review_20260928/models.tex",
    *[f"results/archive/paper_outputs/{name}.tex" for name in ("petersen", "products", "statuses")],
    *[f"results/analysis/general_confirm_r1/{version}/{name}.tex"
      for version in ("9739e8fe30b51d41", "fd04d7ad88883904", "8caaed4049ceb7e9")
      for name in ("summary", "timing")],
]


def export():
    records = []
    for source in SOURCES:
        path = ROOT / source
        original = path.read_bytes()
        translated = original.decode("utf-8")
        for before, after in REPLACEMENTS.items():
            translated = translated.replace(before, after)
        destination = ROOT / "paper/generated/english" / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = translated.encode("utf-8")
        if not destination.exists() or destination.read_bytes() != content:
            destination.write_bytes(content)
        records.append({"source": source, "source_sha256": hashlib.sha256(original).hexdigest(),
                        "translation": destination.relative_to(ROOT).as_posix(),
                        "translation_sha256": hashlib.sha256(content).hexdigest()})
    manifest = ROOT / "paper/generated/english/sources.json"
    text = json.dumps({"purpose": "English presentation only; original numerical values retained",
                       "files": records}, indent=2) + "\n"
    if not manifest.exists() or manifest.read_text() != text:
        manifest.write_text(text)
    index = ROOT / "paper/generated/english/README.md"
    guide = ("# English presentation copies\n\n"
             "Generated from preserved historical LaTeX tables without changing numerical values. "
             "Original snapshots and their manifests remain unchanged. `sources.json` records "
             "both original and translated hashes. Regenerate with `make english-tables`.\n\n"
             + "\n".join(f"- [{r['source']}]({Path(r['translation']).relative_to('paper/generated/english').as_posix()})"
                         for r in records) + "\n")
    if not index.exists() or index.read_text() != guide:
        index.write_text(guide)
    print(f"Prepared {len(records)} English table copies; historical sources unchanged")


if __name__ == "__main__":
    export()
