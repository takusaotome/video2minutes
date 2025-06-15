"""引用サービスのテスト"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.citation_service import CitationService, citation_service
from app.models.chat import Citation


class TestCitationService:
    """引用サービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.citation_service = CitationService()
        self.sample_transcription = """
        こんにちは、皆さん。今日の会議を始めます。
        まず、プロジェクトの進捗について報告します。
        現在、開発は順調に進んでいます。
        次に、課題について話し合いましょう。
        特に品質管理の問題を重点的に検討します。
        """
        self.sample_session = Mock()

    def test_initialization(self):
        """初期化テスト"""
        service = CitationService()
        assert len(service.citation_patterns) == 5
        assert len(service.timestamp_patterns) == 4

    def test_extract_citations_from_response_with_quotes(self):
        """引用符付きテキストからの引用抽出テスト"""
        ai_response = '引用: "プロジェクトの進捗について報告します"と述べています。'
        
        with patch('app.models.chat.Citation') as mock_citation_class:
            mock_citation = Mock()
            mock_citation_class.return_value = mock_citation
            
            citations = self.citation_service.extract_citations_from_response(
                ai_response, self.sample_transcription, self.sample_session
            )
            
            assert len(citations) >= 1

    def test_extract_citations_from_response_with_brackets(self):
        """括弧付きテキストからの引用抽出テスト"""
        ai_response = '「開発は順調に進んでいます」という発言がありました。'
        
        with patch('app.models.chat.Citation') as mock_citation_class:
            mock_citation = Mock()
            mock_citation_class.return_value = mock_citation
            
            citations = self.citation_service.extract_citations_from_response(
                ai_response, self.sample_transcription, self.sample_session
            )
            
            assert len(citations) >= 1

    def test_find_text_position_exact_match(self):
        """完全一致での位置検索テスト"""
        target_text = "プロジェクトの進捗について"
        position = self.citation_service._find_text_position(target_text, self.sample_transcription)
        
        assert position is not None
        assert position > 0

    def test_find_text_position_not_found(self):
        """テキストが見つからない場合のテスト"""
        target_text = "存在しないテキスト"
        position = self.citation_service._find_text_position(target_text, self.sample_transcription)
        
        assert position is None

    def test_normalize_text(self):
        """テキスト正規化テスト"""
        text = "　こんにちは、　世界。　"
        normalized = self.citation_service._normalize_text(text)
        
        assert normalized == "こんにちは 世界"

    def test_extract_important_phrases_brackets(self):
        """括弧内テキスト抽出テスト"""
        text = "「重要な内容」について『詳細な説明』を行います。"
        phrases = self.citation_service._extract_important_phrases(text)
        
        assert "重要な内容" in phrases
        assert "詳細な説明" in phrases

    def test_extract_important_phrases_patterns(self):
        """パターンベース語句抽出テスト"""
        text = "品質についてとても重要です。セキュリティに関して注意が必要です。"
        phrases = self.citation_service._extract_important_phrases(text)
        
        assert len(phrases) >= 1

    def test_calculate_text_similarity_identical(self):
        """同一テキストの類似度テスト"""
        words1 = ["開発", "順調", "進行"]
        words2 = ["開発", "順調", "進行"]
        
        similarity = self.citation_service._calculate_text_similarity(words1, words2)
        assert similarity == 1.0

    def test_calculate_text_similarity_partial(self):
        """部分一致の類似度テスト"""
        words1 = ["開発", "順調", "進行"]
        words2 = ["開発", "順調", "完了"]
        
        similarity = self.citation_service._calculate_text_similarity(words1, words2)
        assert 0.0 < similarity < 1.0

    def test_calculate_text_similarity_no_match(self):
        """不一致の類似度テスト"""
        words1 = ["開発", "順調"]
        words2 = ["品質", "管理"]
        
        similarity = self.citation_service._calculate_text_similarity(words1, words2)
        assert similarity == 0.0

    def test_estimate_timestamp(self):
        """タイムスタンプ推定テスト"""
        position = len(self.sample_transcription) // 2  # 中間位置
        timestamp = self.citation_service._estimate_timestamp(
            position, self.sample_transcription, self.sample_session
        )
        
        assert ":" in timestamp
        assert len(timestamp.split(":")) == 3  # HH:MM:SS形式

    def test_calculate_confidence_exact_match(self):
        """完全一致での信頼度計算テスト"""
        citation_text = "プロジェクトの進捗について報告します"
        position = self.sample_transcription.find(citation_text)
        
        confidence = self.citation_service._calculate_confidence(
            citation_text, self.sample_transcription, position
        )
        
        assert confidence > 0.5

    def test_calculate_confidence_short_text(self):
        """短いテキストの信頼度計算テスト"""
        citation_text = "開発"
        position = self.sample_transcription.find(citation_text)
        
        confidence = self.citation_service._calculate_confidence(
            citation_text, self.sample_transcription, position
        )
        
        assert 0.0 <= confidence <= 1.0

    def test_extract_context(self):
        """文脈抽出テスト"""
        position = self.sample_transcription.find("プロジェクト")
        context = self.citation_service._extract_context(position, self.sample_transcription, 50)
        
        assert len(context) > 0
        assert "プロジェクト" in context

    def test_is_valid_context(self):
        """文脈妥当性チェックテスト"""
        citation_text = "プロジェクト"
        context = "まず、プロジェクトの進捗について報告します。"
        
        is_valid = self.citation_service._is_valid_context(citation_text, context)
        assert is_valid

    def test_is_valid_context_invalid(self):
        """無効な文脈のテスト"""
        citation_text = "存在しないテキスト"
        context = "まず、プロジェクトの進捗について報告します。"
        
        is_valid = self.citation_service._is_valid_context(citation_text, context)
        assert not is_valid

    def test_find_similar_text(self):
        """類似テキスト検索テスト"""
        target_text = "プロジェクト 進捗 報告"
        position, actual_text = self.citation_service._find_similar_text(
            target_text, self.sample_transcription
        )
        
        assert position is not None or actual_text == target_text

    def test_deduplicate_citations(self):
        """重複引用除去テスト"""
        mock_citation1 = Mock()
        mock_citation1.text = "開発は順調です"
        mock_citation1.confidence = 0.8
        
        mock_citation2 = Mock()
        mock_citation2.text = "開発は順調です"  # 重複
        mock_citation2.confidence = 0.6
        
        mock_citation3 = Mock()
        mock_citation3.text = "品質管理が重要"
        mock_citation3.confidence = 0.9
        
        citations = [mock_citation1, mock_citation2, mock_citation3]
        unique_citations = self.citation_service._deduplicate_citations(citations)
        
        assert len(unique_citations) == 2
        assert unique_citations[0].confidence == 0.9  # 最高信頼度が最初

    def test_map_normalized_position(self):
        """正規化位置マッピングテスト"""
        original_text = "こんにちは、　世界！"
        normalized_text = "こんにちは 世界"
        normalized_pos = 5
        
        original_pos = self.citation_service._map_normalized_position(
            normalized_pos, original_text, normalized_text
        )
        
        assert isinstance(original_pos, int)
        assert original_pos >= 0

    def test_create_highlight_info(self):
        """ハイライト情報作成テスト"""
        mock_citation = Mock()
        mock_citation.citation_id = "test-citation-123"
        mock_citation.highlight_start = 10
        mock_citation.highlight_end = 30
        mock_citation.text = "テスト引用"
        mock_citation.start_time = "00:01:30"
        mock_citation.confidence = 0.8
        mock_citation.context = "テスト文脈"
        
        highlight_info = self.citation_service.create_highlight_info(
            mock_citation, self.sample_transcription
        )
        
        assert highlight_info["citation_id"] == "test-citation-123"
        assert highlight_info["start_position"] == 10
        assert highlight_info["end_position"] == 30
        assert highlight_info["highlighted_text"] == "テスト引用"
        assert highlight_info["timestamp"] == "00:01:30"
        assert highlight_info["confidence"] == 0.8
        assert highlight_info["context"] == "テスト文脈"
        assert "created_at" in highlight_info

    def test_create_citation_from_match(self):
        """マッチからの引用作成テスト"""
        import re
        pattern = r'「([^」]+)」'
        text = "「開発は順調に進んでいます」という発言"
        match = re.search(pattern, text)
        
        with patch('app.models.chat.Citation') as mock_citation_class:
            mock_citation = Mock()
            mock_citation_class.return_value = mock_citation
            
            citation = self.citation_service._create_citation_from_match(
                match, self.sample_transcription, self.sample_session
            )
            
            # Citationクラスが呼ばれることを確認
            mock_citation_class.assert_called_once()

    def test_global_citation_service_instance(self):
        """グローバル引用サービスインスタンステスト"""
        assert citation_service is not None
        assert isinstance(citation_service, CitationService)

    def test_empty_text_handling(self):
        """空テキストの処理テスト"""
        empty_transcription = ""
        ai_response = "何らかの回答"
        
        citations = self.citation_service.extract_citations_from_response(
            ai_response, empty_transcription, self.sample_session
        )
        
        assert isinstance(citations, list)

    def test_extract_citations_no_matches(self):
        """マッチしない場合の引用抽出テスト"""
        ai_response = "特に引用がない普通の回答です。"
        
        citations = self.citation_service.extract_citations_from_response(
            ai_response, self.sample_transcription, self.sample_session
        )
        
        assert isinstance(citations, list)