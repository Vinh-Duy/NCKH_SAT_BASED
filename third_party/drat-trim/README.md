# DRAT-trim source snapshot

`drat-trim.c` was retrieved on 2026-10-18 from the authors' [repository](https://github.com/marijnheule/drat-trim), raw source at `https://raw.githubusercontent.com/marijnheule/drat-trim/master/drat-trim.c`. The file retains its complete MIT license header. The included snapshot, rather than the changing upstream branch, identifies the version used here.

It independently checked the supplementary UNSAT proofs and generated LRAT hints using `-p -U -L`. `-p` ignores deletion information and `-U` restricts checking to RUP additions. It is not invoked by the original solver benchmark. Normal package replay uses the standalone Python LRAT checker and does not need a C compiler.

Optional compilation:

```bash
cc -O2 third_party/drat-trim/drat-trim.c -o /tmp/lhk-drat-trim
```
