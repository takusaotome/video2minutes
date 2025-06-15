#!/usr/bin/env python3
"""編集履歴機能のテストスクリプト"""

import difflib
from datetime import datetime

def test_diff_generation():
    """差分生成のテスト"""
    print("=== 差分生成テスト ===")
    
    original = """# 会議議事録

## 出席者
- 田中太郎
- 佐藤花子

## 議題
新しいプロジェクトについて議論しました。
予算は100万円で来月開始予定です。"""

    updated = """# 会議議事録

## 出席者
- 田中太郎
- 佐藤花子
- 鈴木次郎

## 議題
新しいプロジェクトについて議論しました。
予算は150万円で来月開始予定です。

## アクションアイテム
- 田中さん: 詳細設計書の作成 (期限: 来週金曜日)"""

    # unified_diff形式
    print("Unified Diff:")
    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile="編集前",
        tofile="編集後"
    ))
    for line in diff_lines:
        print(line.rstrip())
    
    print("\n" + "="*50 + "\n")

def test_change_analysis():
    """変更分析のテスト"""
    print("=== 変更分析テスト ===")
    
    original = "これは元のテキストです。短い内容です。"
    updated = "これは更新されたテキストです。長い内容になりました。詳細が追加されています。"
    
    # 基本統計
    original_lines = original.split('\n')
    updated_lines = updated.split('\n')
    
    changes = []
    
    if len(updated_lines) > len(original_lines):
        added_lines = len(updated_lines) - len(original_lines)
        changes.append(f"{added_lines}行追加")
    elif len(updated_lines) < len(original_lines):
        removed_lines = len(original_lines) - len(updated_lines)
        changes.append(f"{removed_lines}行削除")
    
    # 文字数変化
    char_diff = len(updated) - len(original)
    if char_diff > 0:
        changes.append(f"{char_diff}文字追加")
    elif char_diff < 0:
        changes.append(f"{abs(char_diff)}文字削除")
    
    print("変更内容:")
    for change in changes:
        print(f"  - {change}")
    
    # 類似度計算
    original_words = set(original.split())
    updated_words = set(updated.split())
    
    if original_words or updated_words:
        intersection = len(original_words & updated_words)
        union = len(original_words | updated_words)
        similarity = intersection / union if union > 0 else 0.0
        print(f"  - 類似度: {similarity:.2f}")

def test_content_hashing():
    """コンテンツハッシュのテスト"""
    print("\n=== コンテンツハッシュテスト ===")
    
    import hashlib
    
    test_contents = [
        "これは最初のバージョンです。",
        "これは2番目のバージョンです。",
        "これは最初のバージョンです。",  # 最初と同じ
    ]
    
    hashes = []
    for i, content in enumerate(test_contents):
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        hashes.append(content_hash)
        print(f"バージョン {i+1}: {content_hash[:8]}... ('{content}')")
    
    # 重複チェック
    if hashes[0] == hashes[2]:
        print("✓ 同じコンテンツは同じハッシュ値を持ちます")
    
    if hashes[0] != hashes[1]:
        print("✓ 異なるコンテンツは異なるハッシュ値を持ちます")

def test_edit_complexity():
    """編集複雑度計算のテスト"""
    print("\n=== 編集複雑度テスト ===")
    
    test_cases = [
        ([], "none"),
        ([{"type": "replace"}], "simple"),
        ([{"type": "replace"}, {"type": "add"}], "moderate"),
        ([{"type": "replace"}, {"type": "add"}, {"type": "delete"}, {"type": "restructure"}], "complex"),
    ]
    
    for edit_actions, expected_complexity in test_cases:
        if len(edit_actions) == 0:
            complexity = "none"
        elif len(edit_actions) == 1:
            complexity = "simple"
        elif len(edit_actions) <= 3:
            complexity = "moderate"
        else:
            complexity = "complex"
        
        print(f"編集アクション数: {len(edit_actions)} -> 複雑度: {complexity}")
        assert complexity == expected_complexity, f"期待値: {expected_complexity}, 実際: {complexity}"

def test_timeline_generation():
    """タイムライン生成のテスト"""
    print("\n=== タイムライン生成テスト ===")
    
    # 模擬編集履歴
    edit_entries = [
        {
            "edit_id": "edit_001",
            "timestamp": "2024-01-15T10:00:00",
            "changes_summary": ["テキスト追加", "セクション追加"],
            "edit_type": "normal"
        },
        {
            "edit_id": "edit_002", 
            "timestamp": "2024-01-15T10:05:00",
            "changes_summary": ["タスク追加"],
            "edit_type": "normal"
        },
        {
            "edit_id": "edit_003",
            "timestamp": "2024-01-15T10:10:00",
            "changes_summary": ["編集を取り消し: edit_002"],
            "edit_type": "undo"
        }
    ]
    
    # 時系列順にソート
    sorted_entries = sorted(edit_entries, key=lambda x: x["timestamp"])
    
    timeline = []
    for i, entry in enumerate(sorted_entries):
        timeline_entry = {
            "timestamp": entry["timestamp"],
            "event_type": entry.get("edit_type", "edit"),
            "description": f"編集 #{i+1}: {', '.join(entry['changes_summary'][:2])}",
            "edit_id": entry["edit_id"]
        }
        timeline.append(timeline_entry)
    
    print("編集タイムライン:")
    for entry in timeline:
        print(f"  {entry['timestamp']} [{entry['event_type']}] {entry['description']}")

def main():
    """メインテスト実行"""
    print("編集履歴機能テスト開始\n")
    
    try:
        test_diff_generation()
        test_change_analysis()
        test_content_hashing()
        test_edit_complexity()
        test_timeline_generation()
        
        print("\n✅ すべてのテストが完了しました")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()