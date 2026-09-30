> Public protocol export from validated development baseline CP000028. Private memory records and private Git history are not included here.

# LLM External Memory Protocol v1.1

## Context Integrity & Deterministic Memory Control Plane Specification

Version: 1.1  
Status: Draft  
Date: 2026-09-28  
Base Specification: LEMP v1.0

---

## 1. 概要

LEMP v1.1 は、LEMP v1.0 の外部永続記憶モデルを拡張し、

> **LLMが必要な記憶を取得・検証したうえで推論を開始するための Deterministic Memory Control Plane**

を定義する。

LEMP v1.0 は主として「忘れても復元できる」ことを目的としていた。

LEMP v1.1 ではさらに、

> **回答する前に、必要な記憶が揃っていることを検証できる**

ことを目的とする。

---

## 2. 背景

LLM は、現在のコンテキストから情報が失われた瞬間を、常に自己認識できるとは限らない。

重要な制約が現在の Working Context から失われた場合、モデル自身が「その制約を忘れた」と認識できる保証はない。

したがって LEMP v1.1 は「何を忘れたかLLM自身に尋ねる」のではなく、

```text
このタスクに必要な情報は何か
↓
その情報は取得済みか
↓
最新版か
↓
矛盾していないか
↓
条件を満たした場合のみ重要な推論に進む
```

という外部検証方式を採用する。

---

## 3. 基本原則

### 3.1 Verify Before Reasoning

重要なタスクでは、推論開始前に必要な Memory が取得済みであることを確認する。

### 3.2 Deterministic Control, Probabilistic Reasoning

可能な限り決定論的に処理する対象:

- checkpoint verification
- state version verification
- required memory verification
- invariant verification
- supersession resolution
- declared conflict detection

LLM が担当する対象:

- 自然言語理解
- 意味的関連性判断
- 推論
- 説明
- 文章生成

### 3.3 Explicit Context Requirements

「このトピックを扱うには何を読まなければならないか」を外部ファイルで定義する。

### 3.4 Critical Invariants

失われると重大な誤判断につながる情報を、通常 Memory とは別に明示する。

### 3.5 Fail Closed for Critical Context

必須Memoryを確認できない場合、重要な LEMP 依存推論では「たぶん大丈夫」として完全なMemory扱いをしない。

### 3.6 Validated Canonical Snapshot

`main` は最新の candidate state を保持するが、それ自体は canonical memory ではない。

canonical memory は、完全な Canonical Gate を通過した特定 commit SHA に対して作成された `lemp-valid/CPxxxxxx` tag が指す snapshot とする。

重要な LEMP 依存推論では:

- 未検証の `main` HEAD を canonical とみなしてはならない;
- 同期開始時に canonical commit SHA を固定しなければならない;
- 1回の同期で異なる commit のファイルを混在させてはならない;
- 新しい candidate が検証失敗した場合、直前の validated canonical snapshot を維持する;
- valid canonical snapshot が存在しない場合は fail closed とする。

この設計により、branch protection は defense-in-depth にはなり得るが、canonical memory の正しさを成立させる必須条件ではない。

---

## 4. システムモデル

```text
                 GitHub Private Repository
                          │
                       main
                    (candidate)
                          │
                          ▼
                ┌─────────────────┐
                │ Canonical Gate  │
                └────────┬────────┘
                         │ PASS only
                         ▼
              lemp-valid/CPxxxxxx tag
                         │
                  pinned commit SHA
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       STATE       Decisions/Events   Archive
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                Memory Control Plane
                         │
         checkpoint / invariant / contract
                         │
                   Integrity Gate
                         │
             ┌───────────┴───────────┐
             │                       │
            PASS                    FAIL
             │                       │
             ▼                       ▼
     Working Context         Recovery / Report
             │
             ▼
            LLM
```

`main` が canonical tag より新しくても、その差分は candidate であり、validated snapshot と混在させない。

---

## 5. Repository 構成

LEMP v1.0 に以下を追加する。

```text
memory-repository/
├── BOOTSTRAP.md
├── MANIFEST.yaml
├── STATE.md
├── INDEX.md
├── SPECIFICATION.md
├── contracts/
│   ├── GLOBAL.yaml
│   └── lemp.yaml
├── invariants/
│   ├── INDEX.yaml
│   ├── INV000001.yaml
│   ├── INV000002.yaml
│   └── ...
├── decisions/
├── events/
├── sessions/
├── archive/
├── topics/
├── tools/
│   └── canonical_status.py
└── .github/workflows/
    └── lemp-canonical.yml
```

Implementations MAY add validation tooling without changing the canonical memory model. The canonical locator convention for v1.1 is `lemp-valid/CPxxxxxx`.

---

## 6. Context Contract

Context Contract は、あるタスク・トピックを扱う際に、最低限どのMemoryを確認する必要があるかを定義する。

例:

```yaml
id: CTX-LEMP
topic: lemp
version: 1

required:
  - STATE.md
  - decisions/D000001.md
  - topics/lemp.md

required_invariants:
  - INV000001
  - INV000002

optional:
  - sessions/S000002.md

archive_policy:
  on_conflict: true
  on_uncertainty: true
  otherwise: false
```

---

## 7. Global Context Contract

すべての長期Memory利用時に適用する最低条件を `contracts/GLOBAL.yaml` に定義する。

最低限:

- MANIFEST / STATE の存在
- checkpoint verification
- state-version verification
- global critical invariant verification
- unresolved critical conflict の検査方針

---

## 8. Critical Invariants

Invariant は、回答や意思決定の際に失われてはいけない重要な事実・制約を表す。

例:

```yaml
id: INV000001
status: active
severity: critical
scope:
  - lemp

statement: "LEMP repository is the canonical persistent memory source."

source:
  decision: D000001

confidence: explicit
```

---

## 9. Invariant Severity

標準レベル:

- `critical`
- `important`
- `advisory`

### critical

未取得または未解決の違反がある場合、重要な LEMP 依存推論を FAIL とする。

### important

追加取得を優先するが、タスクによっては不確実性を明示して続行可能。

### advisory

補助情報。

---

## 10. Pre-Answer Integrity Check

長期Memoryが関係する重要タスクでは、回答前に以下を論理的に確認する。

1. Repository available?
2. Validated canonical tag resolved?
3. Canonical commit SHA pinned?
4. Tag checkpoint matches MANIFEST?
5. MANIFEST loaded from the pinned SHA?
6. Correct checkpoint loaded?
7. STATE loaded from the same SHA?
8. State-Version matches?
9. Context Contract identified?
10. Required memories retrieved from the same snapshot?
11. Critical invariants retrieved?
12. Supersession resolved?
13. Active critical conflicts?

---

## 11. Integrity Gate

結果:

- `PASS`
- `PARTIAL`
- `FAIL`

### PASS

必要条件をすべて満たす。

### PARTIAL

必須ではない情報が不足している。欠落が結論を大きく変えない場合のみ、不確実性を明示して処理可能。

### FAIL

critical context が不足、state/checkpoint検証失敗、または critical conflict が未解決。

原則として追加取得・Recoveryを行う。解決不能なら不足/矛盾を報告する。

---

## 12. Context Integrity Report

概念例:

```text
Context Integrity Report

Repository: available
Checkpoint expected: CP000042
Checkpoint loaded:   CP000042
State version expected: 19
State version loaded:   19

Context Contract:
CTX-PROJECT-ALPHA

Required Memory:
✓ STATE.md
✓ D000041
✓ D000052

Critical Invariants:
✓ INV000001
✓ INV000004

Conflicts:
none

Integrity Status:
PASS
```

---

## 13. 重要な制限

Context Integrity Report は、LLM内部にその情報が絶対に保持され続けていることを証明するものではない。

主に証明できるのは:

- 必要と定義された外部情報を取得した;
- checkpoint が一致した;
- state version が一致した;
- 宣言済みcritical invariantを確認した;
- 既知のcritical conflictが未解決ではない。

`retrieved` と `perfectly remembered and utilized` は同一ではない。

---

## 14. Retrieval Algorithm

```text
User Request
      │
      ▼
Resolve validated canonical tag
      │
      ▼
Pin canonical commit SHA
      │
      ▼
Identify Topic
      │
      ▼
Load GLOBAL Contract from pinned SHA
      │
      ▼
Load MANIFEST / STATE from pinned SHA
      │
      ▼
Determine Required Memory Set
      │
      ▼
Retrieve Missing Memory
      │
      ▼
Load Required Invariants
      │
      ▼
Resolve Supersession
      │
      ▼
Detect Conflicts
      │
      ▼
Integrity Gate
      │
      ├──── FAIL → retrieve / recover
      │
      ▼
     PASS
      │
      ▼
Construct Smallest Sufficient Context
      │
      ▼
LLM Reasoning
```

---

## 15. Smallest Sufficient Context

Context Contract は全履歴を読み込むことを意味しない。

優先順位:

```text
Correctness
>
Required invariants
>
Required current state
>
Relevant decisions
>
Relevant events
>
Relevant sessions
>
Archive
>
Volume
```

---

## 16. Supersession Resolution

古いDecisionを取得しただけで現在状態として採用してはならない。

`supersedes` / `superseded_by` により active と historical を区別する。

---

## 17. Conflict Detection

STATE と Active Decision が矛盾する場合、LLM が推測で片方を採用してはならない。

処理:

1. provenance確認
2. correction event確認
3. supersession確認
4. session確認
5. 必要ならarchive確認
6. 解決不能ならユーザー確認

---

## 18. Forgetting Detection Model

LEMP v1.1 は、

```text
forgetting happened at timestamp X
```

を保証して検出するものではない。

代わりに、

- required memory unavailable
- required memory not retrieved
- checkpoint stale
- state mismatch
- critical invariant missing
- known critical conflict unresolved

を検出する。

つまり **忘却瞬間の検出ではなく Context Integrity 検証**を行う。

---

## 19. Memory Failure Taxonomy

LEMP v1.1 は以下を区別する。

### Storage Loss

GitHub自体に必要情報が存在しない。

### Retrieval Loss

GitHubには存在するが取得されていない。

### Context Loss

取得後、現在のLLM Working Contextから利用できなくなった。

### Compression Loss

要約・圧縮によって詳細が失われた。

### Utilization Failure

情報は存在するがLLMが回答に正しく使用しなかった。

### Synthesis Error

複数のMemoryから誤った結論を生成した。

v1.1 が特に外部検証しやすくするのは Storage verification、Retrieval requirements、Known Conflict、Stale State である。

---

## 20. memory sync v1.1

標準実行経路は `python tools/memory.py sync` とする。統合runtimeはcanonical authorityを先に解決・固定し、その後のvalidation / Applicability / required-memory resolutionを同一snapshot内で実行しなければならない。

標準動作:

1. Locate repository.
2. In normal operation, refresh and prune canonical tags from `origin`, then enumerate `lemp-valid/CPxxxxxx` tags. An explicit no-fetch mode is diagnostic/offline behavior.
3. Validate tag-name/checkpoint correspondence and select the highest valid checkpoint. Every canonical checkpoint, beginning with CP000001, MUST carry an annotated Canonical Gate workflow attestation whose checkpoint/commit/repository/workflow/run-attempt metadata match the tag and pinned commit, and normal canonical resolution MUST remotely verify the exact attested GitHub Actions run attempt; lightweight/local-only attestation is not sufficient canonical authority.
4. If no valid canonical tag exists, return FAIL instead of trusting `main`.
5. Resolve the selected tag to one commit SHA and pin it for the whole sync.
6. Read BOOTSTRAP and MANIFEST from that SHA.
7. Load GLOBAL Context Contract from that SHA.
8. Read STATE from that SHA.
9. Verify tag checkpoint, MANIFEST checkpoint, STATE checkpoint, and state version.
10. Load critical global invariants from that SHA.
11. Load `applicability/INDEX.yaml` and resolve deterministic Memory Entry / Contract Routing.
12. Apply active-session binding and additive semantic candidates; do not allow semantic or summary logic to remove deterministic Contracts. The primary sync runtime MAY accept externally determined known Contract candidates through repeatable `--semantic-contract` arguments, which remain additive-only.
13. Fail closed if an important memory dependency is known but routing remains unresolved; otherwise load all applicable Contracts.
14. Verify Decision↔Contract coverage and materialize required memory, applicable Contract bodies, and required invariant bodies from that SHA into the working context.
15. Collect the selected Contracts' optional paths. Missing safe optional paths yield PARTIAL; unsafe optional path declarations are validation failures.
16. Resolve supersession.
17. Check conflicts.
18. Produce integrity status.
19. When available, compare candidate `main` with the canonical SHA and report newer unvalidated state without mixing it into the canonical context.

---

## 21. memory status v1.1

標準実行経路は `python tools/memory.py status` とする。

最低限以下を表示する。

- Repository
- Canonical tag / commit SHA
- Checkpoint expected / loaded
- State-Version expected / loaded
- Active Context Contract
- Required Memory status
- Critical Invariant status
- Conflict status
- Integrity status
- Candidate ref / SHA / canonical relation when available

Candidate statusはcanonical integrityと分離して報告し、candidate内容をcanonical routingまたはcanonical integrity判定へ混入させてはならない。

---

## 22. memory recall

`memory recall <topic>` では Context Contract を先に確認し、required STATE / decisions / invariantsを取得した後、必要に応じてevents / sessions / archiveへ進む。

---

## 23. memory audit

`memory audit <topic>` は以下を比較する。

- STATE
- Context Contract
- Invariants
- Active Decisions
- Superseded Decisions
- Events
- Sessions
- Archive
- MANIFEST

検査候補:

- contradictions
- stale references
- missing required memory
- broken supersession
- orphan records
- state mismatch
- invalid checkpoint

---

## 24. memory checkpoint v1.1

Durable information extractionと各recordの意味判断はLLM/user側で行い、checkpoint runtimeは準備済みdurable changesのfinalizerとして動作する。

標準finalizerは `python tools/memory.py checkpoint` とする。

保存準備時には以下を評価する。

1. Durable information extraction
2. State changes
3. Decision changes
4. Event creation
5. Invariant impact
6. Context Contract / Applicability impact
7. Session update
8. Archive/source-recovery update
9. INDEX update
10. MANIFEST update
11. Checkpoint increment

Finalizerは少なくとも以下を機械的に要求する。

1. named candidate branch（`main` direct finalizationはdefault deny）
2. candidate HEAD がcurrent canonical SHAのdescendant
3. candidate checkpoint がcurrent canonical checkpointからexactly +1
4. structural / Applicability / provenance / archive validation PASS
5. regression suite PASS
6. current canonical SHAからcandidate HEADまでのcommitted deltaと、staged/unstaged/untracked working-tree pathsのunionがLEMP managed-path allowlist内だけであることを確認
7. full canonical→candidate candidate path setをcandidate worktree上でlocal checkpoint scanし、symlink/binary/non-UTF-8/oversized/sensitive filename/detectable secretをFAIL
8. `git add -A`を使用せず、検証済みcurrent pathだけを明示stage
9. validated durable changesを一つのcandidate commitとして作成
10. Canonical Gateはpromotion前にcanonical→candidate committed deltaのmanaged-path検査を再実行

candidate commitの作成はcanonical promotionではない。Canonical Gate成功前に新checkpointをcanonicalとして扱ってはならない。

---

## 25. Invariant Update Policy

Invariant にする候補:

- 違反すると重大な誤判断につながる;
- 長期間有効;
- 多くのセッションで必要;
- 明示的な根拠がある。

単なる雑談や一時的情報をInvariantにしない。

---

## 26. Context Contract Generation

Context Contract は以下をスコープに作成できる。

- Project
- Topic
- Workflow
- Role
- High-impact task

例:

```text
contracts/coding.yaml
contracts/business-plan.yaml
contracts/lemp.yaml
contracts/project-alpha.yaml
```

---

## 27. Deterministic Control Plane

制御層が担当すべきもの:

- file existence
- version equality
- checkpoint equality
- required-list membership
- status field
- supersession links
- schema validity when schemas exist
- declared conflict flags/checks

これらは可能な限りLLMの主観的自己評価に依存させない。

---

## 28. Probabilistic Reasoning Layer

LLMが担当するもの:

- deterministic routingで解決できない user intent / semantic relevance の追加候補発見
- explanation
- reasoning
- alternative generation
- natural-language synthesis

ただし semantic判断はApplicability Control Planeのdeterministic minimum setを削除するauthorityを持たない。

---

## 29. Decision Boundary

```text
Control Plane
→ 「宣言された条件上、考えてよい状態か」を決める

LLM
→ 「与えられた文脈をどう解釈し、どう考えるか」を担当する
```

---

## 30. Security

LEMP v1.0 のセキュリティ要件を継承する。

禁止:

- Password
- API key
- OAuth token
- SSH private key
- Session cookie
- Recovery code
- Private encryption key
- その他認証秘密情報

Context Contract や Invariant にも秘密情報を直接記録してはならない。

`memory checkpoint` はcheck-only成功またはcandidate commit作成前に、canonical→candidateのcomplete candidate path setをcandidate worktree上でlocal checkpoint scanしなければならない。scannerはdetectable secretに加え、symlink/binary/non-UTF-8/oversized/sensitive filenameも拒否する。CI full-history Gitleaksはhistory-awareな別レイヤーとして維持する。

---

## 31. Failure Modes

### Repository unavailable

```text
Integrity: FAIL
Reason: external memory unavailable
```

### Required Memory missing

```text
Integrity: FAIL
Reason: required context unavailable
```

### State version mismatch

```text
Integrity: FAIL
Reason: stale or inconsistent state
```

### Optional context missing

```text
Integrity: PARTIAL
```

### Critical invariant missing

```text
Integrity: FAIL
```

### Conflict unresolved

```text
Integrity: FAIL
```

---

## 32. Recommended Commands

- `memory sync`
- `memory status`
- `memory recall <topic>`
- `memory audit <topic>`
- `memory checkpoint`
- `memory integrity`
- `memory invariants`
- `memory contract <topic>`

---

## 33. memory integrity

現在のタスクに宣言された必要情報が揃っているか検査する。

概念例:

```text
Checkpoint: PASS
State-Version: PASS
Required Context: PASS
Critical Invariants: PASS
Conflicts: PASS

Overall: PASS
```

---

## 34. Typical Workflow

```text
New Chat
   ↓
memory sync
   ↓
Applicability resolution
   ↓
Contract coverage
   ↓
Context Integrity PASS
   ↓
User Work
   ↓
Task changes
   ↓
Applicability re-resolution
   ↓
Required context verification
   ↓
Reasoning
   ↓
Important durable change
   ↓
memory checkpoint
```

---

## 35. 長期運用モデル

数年運用して大量のSessions/Events/Decisionsが存在しても、全件をコンテキストに入れる必要はない。

現在の質問に必要な Global Contract + Current STATE + Topic Contract + relevant Decisions + required Invariants を中心に取得する。

---

## 36. Acceptance Criteria

LEMP v1.1 実装は最低限以下を満たす。

1. タスク/トピックごとに Required Context を定義できる。
2. Critical Invariant を定義できる。
3. Checkpointを機械的に比較できる。
4. State-Versionを機械的に比較できる。
5. 必須Memoryの取得漏れを検出できる設計を持つ。
6. active / superseded Decisionを区別できる。
7. Known critical conflictをFAILとして扱える。
8. Integrity PASS/PARTIAL/FAILを生成できる。
9. FAIL状態では追加取得/Recoveryを要求できる。
10. 原記録へのRecovery Pathを維持する。
11. 全履歴を毎回ロードせず運用できる。
12. LLMの自己申告だけで記憶完全性を判断しない。
13. deterministic Memory Entry / Contract Routingをmachine-readableに定義できる。
14. active DecisionとContext Contract required-setのcoverageを双方向に検証できる。
15. summary/semantic routingがdeterministic minimum setを削除できない。
16. unresolved important memory routingをFAILとして扱える。
17. CP000001を含むすべてのcanonical tagについてannotated workflow attestationを検証し、lightweight/manual tagだけではcanonicalにしない。
18. checkpoint finalizerがmanaged path allowlistを強制し、stage-allを行わない。
19. checkpoint commit前にdetectable secretを検査してFAILできる。
20. configured semantic hintsをadditive-only candidateとして扱い、deterministic minimum setを削除しない。
21. normal canonical resolutionの前にorigin canonical tagsをrefresh/pruneし、古いlocal tag集合だけを暗黙に最新authorityとして扱わない。
22. `memory sync` がrequired memoryとrequired invariantの本文を同一pinned snapshotからmaterializeしてworking contextとして返せる。
23. checkpoint managed-path検査がcanonical→candidate committed deltaとcurrent working-tree changesの両方を覆い、Canonical Gateでもpromotion前に再検査される。
24. canonical attestation remote verificationがtagに記録されたexact workflow run attemptを検証し、後続rerunによって既存のsuccessful attestationが無効化されない。
25. same checkpoint tagが同一commitを指し、既存attested attemptがremoteでcompleted non-successと確認された場合に限り、successful gate後にannotated tag objectだけをforce-with-leaseでrecoverできる。peeled commitを変更してはならない。
26. Canonical Gateがpromotion後にnormal remote-attested `memory sync`を実行し、exact promoted tag/checkpoint/SHA、PASS、required context/invariant materializationを確認できる。
27. 同じpost-promotion gateで`memory status`がpromoted SHAを`CURRENT`として報告することを確認できる。
28. `memory sync` / `memory status` がrequired/critical checks PASS後、safe optional contextのみ不足する場合にPARTIALを返し、missing optional pathsを報告できる。
29. `memory sync --semantic-contract CTX-ID` がknown Contractをadditive candidateとしてpinned-snapshot Applicabilityへ渡せ、unknown candidateがrequire-memory fail-closedを迂回できない。
30. optional Contract pathもrepository safe-path boundaryを満たし、unsafe optional pathがPARTIALではなくvalidation FAILになる。
31. checkpoint file-safety/secret scanがcurrent worktree changesだけでなくcomplete canonical→candidate candidate path setをcandidate worktree上で検査し、既commitのmanaged symlink/binary/non-UTF-8/oversized/sensitive fileもpromotion前にFAILできる。
32. LEMP CI workflowのcheckout/setup-python Action refがexact commit SHAへ固定され、direct Python validator dependencyがrepository-managed fileでexact version pinされる。

---

## 37. 非目標

LEMP v1.1 は以下を保証しない。

- LLM内部コンテキストの完全な観測
- 忘却が発生した正確な瞬間の検出
- LLMが取得情報を必ず正しく利用する保証
- hallucinationの完全排除
- 完全決定論的な自然言語推論
- GitHub障害時の完全継続

---

## 38. 設計上の重要な区別

LEMP v1.1 は Memory completeness そのものを完全に証明するわけではない。

代わりに **Deterministically modeled Applicability + Declared Context Requirements に対する完全性**を検証する。

つまり、

> 「すべてを覚えている」

ではなく、

> **「この判断に適用されると機械的に定義されたContractを落とさず、そのContractに必要と宣言された情報をすべて確認した」**

を外部検証可能にする。

---

## 39. 基本思想

LEMP v1.0:

> The system must make important information recoverable.

LEMP v1.1:

> **The system must verify required information before reasoning.**

日本語では、

> **LLMが忘れないことを期待するのではなく、必要な記憶を確認しなければ重要な推論に進めない仕組みを作る。**

---

## 39.1 Archive / Source-Recovery Persistence Policy

Checkpointed Session の復旧可能性を、要約だけに依存させてはならない。

永続化ルール:

1. canonical checkpoint を進める Session は、対応する source-recovery archive を **exactly one** 持たなければならない。
2. machine-readable な対応関係は `archive/INDEX.yaml` に記録する。
3. archive record は、Session/Event の短い要約だけでは失われ得る durable evidence、判断理由、検証結果、運用上の制約を復元できる粒度を持つ。
4. archive record は会話全文の逐語 transcript である必要はない。
5. archive record に secret を保存してはならない。
6. archive record は immutable-preferred とし、歴史的意味の訂正は可能な限り新しい Event / Session / recovery record で明示する。
7. `archive/INDEX.yaml` は control-plane の小さい索引として通常取得してよいが、archive 本文は conflict、uncertainty、source verification、または source-level reconstruction が必要な場合にのみ取得する。
8. recursive summary を唯一の historical truth としてはならない。

`MANIFEST.yaml.archive_policy.checkpointed_session_archive_required: true` はこの永続化ルールを宣言する。

---

## 39.2 Applicability Control Plane

LEMP v1.1 は、Context Integrity の前段に Applicability Control Plane を持つ。

```text
User Request
      ↓
Memory Entry
      ↓
Contract Routing
      ↓
Contract Coverage
      ↓
Integrity Gate
      ↓
LLM Reasoning
```

### 39.2.1 Memory Entry

外部永続Memoryを参照すべきことが決定論的に分かる場合、Memory Entryを有効にする。

決定論的根拠には少なくとも以下を使用できる:

- 明示的な `memory ...` command;
- Contract / Decision / repository resource identifier;
- machine-readable routing table;
- active memory-session binding.

要約文だけを根拠として「Memory不要」と判定してはならない。

### 39.2.2 Contract Routing

`applicability/INDEX.yaml` は決定論的routingのmachine-readable sourceとする。

deterministic routing が選択したContractは、LLMまたはsemantic retrievalによって削除してはならない。

semantic routing は **additive-only** とし、追加候補を提示できるが、deterministic minimum setを縮小できない。`applicability/INDEX.yaml.routing.semantic_hints` のconfigured patternは自然言語paraphraseを追加候補へ変換できるが、deterministic authorityには昇格しない。

重要タスクで複数Contractが妥当な場合はcandidate Contractのunionを使用する。重要なMemory依存が既知であるにもかかわらずroutingを解決できない場合は fail closed とする。

### 39.2.3 Contract Coverage

active Decision は `decisions/INDEX.yaml` 上でContext Contractへの影響をmachine-readableに宣言する。

```yaml
context_impact:
  mode: required
  contracts:
    - CTX-LEMP
```

validator は少なくとも以下を双方向に確認する:

```text
Decision requires Contract
      ↓
Decision path exists in Contract.required

Contract.required contains Decision
      ↓
Decision declares that Contract
```

これにより、Integrity Gateが検査するrequired set自体の機械的なcoverageを強化する。

### 39.2.4 Summary Independence

Summary、Topic prose、Session summaryは検索・説明の補助には使用できるが、deterministic required setを削除するauthorityにはしない。

テストでは「現実的な誤要約」を完全列挙しようとせず、summary本文を任意内容へ置換してもdeterministic routingおよびrequired-memory setが変わらない性質を検証する。

### 39.2.5 Failure Taxonomy追加

LEMPは以下を追加で区別する:

- **Entry Loss** — Memory依存要求をMemory非依存として処理する。
- **Routing Loss** — 必要なContext Contractを選択しない。
- **Coverage Loss** — 適切なContractを選んだが、そのrequired setに必要なMemoryが宣言されていない。

これらは Retrieval Loss / Context Loss / Compression Loss / Utilization Failure と別のfailure classである。

### 39.2.6 Guarantee Boundary

Applicability PASS は arbitrary natural-language semantic completeness の証明ではない。

特に、明示identifierもmachine-readable routeもなく、過去Memoryへの依存が自然言語の意味からのみ推測可能な場合、その発見はprobabilisticである。

LEMPの決定論的保証は、explicit/deterministic routing、session binding、declared Decision coverage、fail-closed policy、およびそれらの構造検証に限定される。


---

## 40. Reference Architecture

```text
┌─────────────────────────────────────────┐
│        GitHub Persistent Memory         │
│                                         │
│ STATE / Decisions / Events / Archive    │
│ Contracts / Invariants / MANIFEST       │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       Applicability Control Plane       │
│                                         │
│ memory entry / contract routing         │
│ decision-contract coverage              │
│ additive semantic candidates            │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│      Deterministic Memory Control       │
│                 Plane                   │
│                                         │
│ checkpoint verification                 │
│ state-version verification              │
│ context-contract verification           │
│ invariant verification                  │
│ supersession resolution                 │
│ conflict detection                      │
└───────────────────┬─────────────────────┘
                    │
              Integrity Gate
                    │
             PASS / FAIL
                    │
                    ▼
┌─────────────────────────────────────────┐
│          Working Context                │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          Probabilistic LLM              │
│                                         │
│ understanding                           │
│ reasoning                               │
│ synthesis                               │
│ response generation                     │
└───────────────────┬─────────────────────┘
                    │
                    ▼
              Memory Extraction
                    │
                    ▼
              Git Checkpoint
```

---

## 41. Normative Summary

LEMP v1.1 implementation:

- **MUST** preserve LEMP v1.0 external-memory principles.
- **MUST** distinguish the candidate branch from validated canonical snapshots.
- **MUST NOT** treat an unvalidated `main` HEAD as canonical solely because it is newer.
- **MUST** resolve canonical memory through a validated `lemp-valid/CPxxxxxx` snapshot reference.
- **MUST** require a valid annotated Canonical Gate workflow attestation for every canonical tag beginning with CP000001; matching tag name and MANIFEST checkpoint alone are insufficient.
- **MUST** remotely verify the exact attested Canonical Gate run attempt for normal canonical authority at every checkpoint beginning with CP000001 and fail closed when verification cannot be established.
- **MUST** keep an already successful attested attempt valid across later workflow reruns.
- **MUST NOT** move the peeled commit of an existing canonical checkpoint tag during recovery.
- **MAY** replace only the annotated tag object when its prior attested attempt is remotely confirmed completed without success, but the replacement MUST follow a successful new gate and MUST use force-with-lease against the observed prior tag ref.
- **MUST NOT** treat explicit offline/local-only attestation mode as canonical authority for important LEMP-dependent reasoning.
- **MUST** pin one canonical commit SHA for each synchronization and MUST NOT mix files from different commits.
- **MUST** resolve and pin canonical authority before using Applicability, Contracts, State, or required memory for primary sync/status execution.
- **MUST** keep candidate-state reporting separate from canonical integrity and MUST NOT allow a newer candidate to contaminate canonical synchronization.
- **MUST** keep the previous validated canonical snapshot when a newer candidate fails validation.
- **MUST** validate each one-checkpoint-newer candidate with validators and checkpoint scanning loaded from the immediately previous canonical checkpoint, in addition to candidate-native checks.
- **MUST** derive previous-generation authority as exactly candidate checkpoint minus one and verify that exact tag with the previous canonical snapshot's own canonical verifier.
- **MUST NOT** describe previous-generation validation as an independent trust root while its invocation workflow remains repository-controlled.
- **MUST** execute the normal remote-attested `memory sync` path after canonical promotion and require the exact promoted tag/checkpoint/SHA with Integrity PASS.
- **MUST** verify that post-promotion sync materializes all declared required context and required invariant bodies.
- **MUST** execute post-promotion `memory status` against the promoted SHA and require candidate relation `CURRENT`.
- **MUST** fail closed when no valid canonical snapshot can be resolved.
- **MUST** verify checkpoint and state version during synchronization.
- **MUST** support explicit required context.
- **MUST** distinguish required from optional memory.
- **MUST** produce `PARTIAL` after required/critical checks pass when only safe optional context is unavailable, and MUST identify the missing optional paths without discarding required working context.
- **MUST** apply the repository path-safety boundary to optional path declarations; unsafe optional declarations are validation failures.
- **MUST** support critical invariants.
- **MUST** detect missing declared required memory.
- **MUST** maintain deterministic Applicability routing metadata.
- **MUST NOT** allow summary or semantic routing to remove deterministically required Contracts or memory.
- **MUST** validate declared Decision↔Contract coverage.
- **MUST** fail closed when an important known memory dependency remains unresolved.
- **MUST** preserve supersession history.
- **MUST** maintain a machine-readable source-recovery archive index.
- **MUST** preserve exactly one registered source-recovery archive for every Session that advances the canonical checkpoint.
- **MUST** validate a prepared checkpoint candidate before finalization and MUST NOT treat candidate commit creation as canonical promotion.
- **MUST** reject checkpoint changes outside the managed path allowlist and MUST NOT use stage-all behavior such as `git add -A` for checkpoint finalization.
- **MUST** scan the complete canonical-to-candidate checkpoint path set in the candidate worktree before check-only success or candidate commit creation, rejecting unsafe file forms and detectable secrets even when the affected managed file was already committed on the candidate branch.
- **MUST** keep explicit checkpoint staging limited to validated current worktree changes; broader candidate scanning MUST NOT imply stage-all behavior.
- **MUST** pin repository-used first-party checkout/setup-python Actions to exact commit SHAs and MUST install direct CI validation dependencies from repository-managed exact-version constraints.
- **MUST NOT** describe Action/direct-version pinning alone as a fully hermetic or external cryptographic trust root when transitive hashes, runner images, interpreter patch selection, or workflow authority remain variable.
- **MUST NOT** rely on recursively summarized summaries as the sole historical recovery source.
- **MUST** report unresolved critical conflicts.
- **MUST NOT** use model self-reported memory completeness as the only integrity mechanism.
- **MUST NOT** claim to detect every internal forgetting event.
- **SHOULD** perform integrity verification before important LEMP-dependent reasoning.
- **SHOULD** use deterministic checks wherever possible.
- **SHOULD** minimize the final Working Context.
- **SHOULD** fail closed when critical information is unavailable.
- **MAY** use semantic retrieval, configured semantic hint patterns, or explicit `memory sync --semantic-contract` candidates to identify candidate Contracts, but only additively with respect to deterministic applicability. Unknown semantic candidates MUST NOT satisfy an otherwise unresolved required-memory dependency.
- **MAY** automate schema and integrity validation.

## 31. Previous-Generation Validator Compatibility

Canonical promotion requires a backward-looking validation pass from the immediately previous canonical checkpoint. The previous generation validates the candidate repository state using its own structural, applicability, provenance, archive, and checkpoint-file scanner implementations.

This mechanism constrains one-step self-weakening and makes validator changes compatibility-sensitive. It does not create cryptographic independence because the invoking workflow remains in the candidate-controlled repository.

Acceptance requirements:

1. candidate checkpoint is exactly previous canonical checkpoint + 1;
2. candidate descends from the previous canonical commit;
3. the exact previous canonical tag is verified by the previous snapshot's own canonical verifier;
4. previous structural/applicability/provenance/archive validators all accept the candidate;
5. previous checkpoint scanner accepts the complete previous-canonical→candidate path set;
6. removing the declared policy or Canonical Gate invocation is a structural validation failure.

---

End of LEMP v1.1 Draft Specification
