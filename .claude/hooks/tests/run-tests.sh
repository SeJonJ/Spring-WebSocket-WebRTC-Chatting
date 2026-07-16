#!/usr/bin/env bash
# run-tests.sh — Hook 회귀 테스트 러너 (python3 단독, 외부 의존 0)
#
# 각 케이스를 격리된 임시 PROJECT_ROOT(sandbox 복사본)에서 실행해
# exit code / stdout 포함·미포함 / 생성 파일을 검증한다.
# bats/shellcheck 불필요 — python3 만 있으면 동작.
#
# 사용: bash .claude/hooks/tests/run-tests.sh
# EXIT: 0=전체 통과 / 1=실패 존재

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"   # .../.claude/hooks/tests
HOOKS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"     # .../.claude/hooks
PROJECT_ROOT="$(cd "$HOOKS_DIR/../.." && pwd)"

exec python3 - "$SCRIPT_DIR" "$HOOKS_DIR" "$PROJECT_ROOT" <<'PYEOF'
import datetime, json, os, shutil, subprocess, sys, tempfile

test_dir, hooks_dir, project_root = sys.argv[1], sys.argv[2], sys.argv[3]
today = datetime.date.today().strftime('%Y-%m-%d')
cases_path = os.path.join(test_dir, 'cases.tsv')
fixtures_dir = os.path.join(test_dir, 'fixtures')
sandbox_dir = os.path.join(test_dir, 'sandbox')
generated_sandboxes = {'empty', 'with-declared-l3', 'with-session-log'}

def dash(v):
    return None if v.strip() == '-' else v

def legacy_profile(strategy):
    return {
        'risk': {
            'desktop_block_glob': 'chatforyou-desktop/src/**',
            'desktop_block_hint': 'nodejs-frontend 원본 수정 후 동기화',
            'l0_pass_globs': ['**/*.md'],
            'l1_path_globs': ['nodejs-frontend/static/js/**'],
            'l2_path_globs': ['springboot-backend/src/main/**'],
            'l3_filename_globs': ['*kurento*'],
            'l2_content_keywords': ['RedisTemplate', 'JwtTokenProvider'],
            'l3_content_keywords': ['RTCPeerConnection', 'WebRtcEndpoint'],
            'content_l3_enforce': 'advisory',
            'plan_glob': 'plan_docs/**/*.md',
            'l3_review_strategy': strategy,
            'review_patterns': [],
        },
        'file_type_map': [
            {'glob': 'springboot-backend/src/main/**', 'type': 'backend-main'},
            {'glob': 'springboot-backend/src/test/**', 'type': 'backend-test'},
            {'glob': 'nodejs-frontend/static/js/**', 'type': 'frontend-js'},
            {'glob': 'plan_docs/**', 'type': 'plan-doc'},
        ],
        'skip_untyped': True,
        'phase4_trigger_glob': 'plan_docs/04-analyze/*.md',
        'checklist_scan_targets': [
            {'label': '03-implementation', 'glob': 'plan_docs/03-implementation/*.md', 'is_impl': True},
            {'label': 'backend plan_docs', 'glob': 'springboot-backend/plan_docs/*.md'},
            {'label': 'frontend plan_docs', 'glob': 'nodejs-frontend/plan_docs/*.md'},
        ],
        'pdca': {'enabled': False},
        'compliance': {
            'activity_groups': [{'label': 'backend', 'types': ['backend-main', 'backend-test']}],
            'plan_types': ['plan-doc'],
            'plan_gate_code_types': ['backend-main', 'backend-test', 'frontend-js'],
            'convention_reminder': {},
        },
        'output_contract': {'markers': {}},
        'knowledge_capture': {'vault_path': ''},
    }

passed, failed = 0, 0
failures = []

with open(cases_path, encoding='utf-8') as f:
    for raw in f:
        line = raw.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        cols = line.split('\t')
        if len(cols) < 8:
            print(f"⚠️  형식 오류(8컬럼 필요): {line[:60]}")
            failed += 1
            continue
        name, hook, sandbox, fixture, exp_exit, must, mustnot, expect_file = [c.strip() for c in cols[:8]]
        sandbox, must, mustnot, expect_file = map(dash, (sandbox, must, mustnot, expect_file))

        tmp = tempfile.mkdtemp(prefix='hooktest-')
        try:
            shutil.copytree(
                os.path.join(project_root, 'scripts', 'sage_harness', 'hooks'),
                os.path.join(tmp, 'scripts', 'sage_harness', 'hooks'),
                dirs_exist_ok=True,
            )
            os.makedirs(os.path.join(tmp, 'sage'), exist_ok=True)
            profile_path = os.path.join(tmp, 'sage', 'project-profile.json')
            with open(profile_path, 'w', encoding='utf-8') as pf:
                json.dump(legacy_profile('claude_grep_first'), pf)
            if sandbox:
                src = os.path.join(sandbox_dir, sandbox)
                if os.path.isdir(src):
                    shutil.copytree(src, tmp, dirs_exist_ok=True)
                elif sandbox not in generated_sandboxes:
                    raise FileNotFoundError(src)
            log_dir = os.path.join(tmp, '.claude', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            if sandbox == 'with-declared-l3':
                with open(os.path.join(log_dir, 'declared-risk-test.json'), 'w', encoding='utf-8') as wf:
                    wf.write('{"level":"L3","ts":"2026-06-10T00:00:00Z","excerpt":"declared L3"}\n')
            elif sandbox == 'with-session-log':
                with open(os.path.join(log_dir, 'session-TODAY.jsonl'), 'w', encoding='utf-8') as wf:
                    wf.write('{"ts":"2026-06-10T00:00:00Z","tool":"Edit","file":"springboot-backend/src/main/java/Foo.java","type":"backend-main","branch":"test","session":"test"}\n')
            # os.walk 사용 — glob('**')는 .claude 등 숨김 디렉토리를 건너뛴다
            for root, _dirs, files in os.walk(tmp):
                for fn in files:
                    p = os.path.join(root, fn)
                    if 'TODAY' in fn:
                        os.rename(p, os.path.join(root, fn.replace('TODAY', today)))
                    elif fn.endswith('.md'):
                        os.utime(p, None)

            with open(os.path.join(fixtures_dir, fixture), 'rb') as ff:
                stdin_bytes = ff.read()
            stdin_bytes = stdin_bytes.replace(b'/x/', (tmp + os.sep).encode())

            env = dict(os.environ, CLAUDE_PROJECT_DIR=tmp, SAGE_PROFILE=profile_path)
            proc = subprocess.run(
                ['bash', os.path.join(hooks_dir, hook)],
                input=stdin_bytes, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
            )
            out = proc.stdout.decode('utf-8', 'replace')

            errs = []
            if proc.returncode != int(exp_exit):
                errs.append(f"exit {proc.returncode} != {exp_exit}")
            if must and must not in out:
                errs.append(f"stdout 에 '{must}' 없음")
            if mustnot and mustnot in out:
                errs.append(f"stdout 에 '{mustnot}' 있으면 안 됨")
            if expect_file:
                rel, _, sub = expect_file.partition('::')
                rel = rel.replace('{TODAY}', today)
                fpath = os.path.join(tmp, rel)
                if not os.path.exists(fpath):
                    errs.append(f"파일 미생성: {rel}")
                elif sub and sub != '-':
                    content = open(fpath, encoding='utf-8', errors='replace').read()
                    if sub not in content:
                        errs.append(f"{rel} 에 '{sub}' 없음")

            if errs:
                failed += 1
                failures.append((name, errs, out.strip()[:200]))
                print(f"❌ {name}: {'; '.join(errs)}")
            else:
                passed += 1
                print(f"✅ {name}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

print()
print(f"=== 결과: {passed} passed, {failed} failed ===")
if failures:
    print("\n실패 상세:")
    for name, errs, out in failures:
        print(f"  • {name}: {'; '.join(errs)}")
        if out:
            print(f"    stdout: {out}")
sys.exit(1 if failed else 0)
PYEOF
