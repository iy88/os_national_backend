"""
修复 File 表中 secure_filename 扩展名与 original_filename 不一致的脏数据。

历史 bug 根因：utils/file_utils.py:save_avatar_file 对纯中文文件名
（如 "张老三.png"）经 secure_filename 处理后扩展名丢失（变成 "png"），
触发 `'.' in original_filename` 检查为 False，错误地 fallback 到 'jpg'。

本脚本对每条 secure_ext != original_ext 的记录：
1. 抽取 secure_filename 中的 UUID 部分（第一个 '.' 之前）
2. 拼接新 secure_filename = f"{uuid}.{original_ext}"
3. 物理文件 rename（uploads/files/{old} -> {new}）
4. 更新 DB 字段

每条独立 commit，错误不阻断后续记录。

用法:
    python scripts/fix_file_extensions.py          # 交互式：先列出再确认
    python scripts/fix_file_extensions.py --apply  # 直接执行（无确认）
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from config import Config  # noqa: E402
from models import db, File  # noqa: E402


def _ext(filename: str) -> str:
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def _build_plan():
    """query DB + filesystem，返回待修复列表。"""
    plan = []
    with app.app_context():
        for f in File.query.order_by(File.fid).all():
            orig_ext = _ext(f.original_filename or '')
            sec_ext = _ext(f.secure_filename or '')
            if not orig_ext or orig_ext == sec_ext:
                continue

            # 抽取 secure_filename 的 UUID 部分
            if '.' not in (f.secure_filename or ''):
                plan.append({
                    'fid': f.fid, 'original_filename': f.original_filename,
                    'old_secure': f.secure_filename, 'new_secure': None,
                    'old_path': None, 'new_path': None,
                    'status': 'skip', 'reason': 'secure_filename has no dot',
                })
                continue

            uuid_part = f.secure_filename.rsplit('.', 1)[0]
            new_secure = f"{uuid_part}.{orig_ext}"
            old_path = os.path.join(Config.UPLOAD_FOLDER, f.secure_filename)
            new_path = os.path.join(Config.UPLOAD_FOLDER, new_secure)

            status = 'ok'
            reason = ''
            if not os.path.exists(old_path):
                status = 'skip'
                reason = 'physical file missing'
            elif os.path.exists(new_path):
                status = 'skip'
                reason = f'target already exists: {new_secure}'

            plan.append({
                'fid': f.fid, 'original_filename': f.original_filename,
                'old_secure': f.secure_filename, 'new_secure': new_secure,
                'old_path': old_path, 'new_path': new_path,
                'status': status, 'reason': reason,
            })
    return plan


def _print_plan(plan):
    ok = [p for p in plan if p['status'] == 'ok']
    skip = [p for p in plan if p['status'] == 'skip']
    print(f'Total mismatched: {len(plan)}  (will fix: {len(ok)}, will skip: {len(skip)})\n')

    print('=== Will FIX (rename file + update DB) ===')
    for p in ok:
        print(f"  fid={p['fid']:<4d}  orig={p['original_filename']!r}")
        print(f"             old_secure={p['old_secure']!r}")
        print(f"             new_secure={p['new_secure']!r}")
    print()

    if skip:
        print('=== Will SKIP ===')
        for p in skip:
            print(f"  fid={p['fid']:<4d}  orig={p['original_filename']!r}  "
                  f"old={p['old_secure']!r}  reason={p['reason']}")
        print()


def _apply(plan):
    fixed = skipped = failed = 0
    with app.app_context():
        for p in plan:
            if p['status'] != 'ok':
                skipped += 1
                continue
            try:
                os.rename(p['old_path'], p['new_path'])

                row = File.query.get(p['fid'])
                row.secure_filename = p['new_secure']
                db.session.commit()
                fixed += 1
                print(f"  [ok]   fid={p['fid']}  {p['old_secure']} -> {p['new_secure']}")
            except Exception as e:
                db.session.rollback()
                failed += 1
                print(f"  [fail] fid={p['fid']}: {e}")

    print(f'\nDone. fixed={fixed}, skipped={skipped}, failed={failed}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='Actually perform the rename + DB update (default: dry-run only)')
    args = parser.parse_args()

    plan = _build_plan()
    if not plan:
        print('No mismatched files found. Nothing to do.')
        return

    _print_plan(plan)

    if not args.apply:
        print('Dry-run only. Re-run with --apply to perform changes.')
        return

    confirm = input(f'Proceed to fix {sum(1 for p in plan if p["status"] == "ok")} files? [y/N] ')
    if confirm.strip().lower() != 'y':
        print('Aborted.')
        return

    _apply(plan)


if __name__ == '__main__':
    main()
