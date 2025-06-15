"""引用機能とハイライト管理サービス"""
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.chat import Citation, ChatMessage, ChatSession
from app.utils.logger import get_logger

logger = get_logger(__name__)

class CitationService:
    """引用とハイライト管理サービス"""
    
    def __init__(self):
        # 引用パターンの定義
        self.citation_patterns = [
            r'引用[:：]\s*"([^"]+)"',
            r'「([^」]+)」(?:という|と言う|と述べ)',
            r'文字起こしの(\d+分\d+秒?)部分',
            r'(\d{2}:\d{2}:\d{2})(?:から|時点)の発言',
            r'音声の(\d+:\d+)あたり',
        ]
        
        # タイムスタンプパターン
        self.timestamp_patterns = [
            r'(\d{1,2}):(\d{2}):(\d{2})',  # HH:MM:SS
            r'(\d{1,2}):(\d{2})',         # MM:SS
            r'(\d+)分(\d+)秒',           # X分Y秒
            r'(\d+)分',                  # X分
        ]
    
    def extract_citations_from_response(
        self,
        ai_response: str,
        transcription: str,
        session
    ):
        """
        AI回答から引用を抽出
        
        Args:
            ai_response: AI回答テキスト
            transcription: 元の文字起こし
            session: チャットセッション
        
        Returns:
            List: 抽出された引用リスト
        """
        logger.info("AI回答から引用を抽出開始")
        
        # Import Citation at runtime to avoid circular imports
        from app.models.chat import Citation
        
        citations = []
        
        # パターンベース引用抽出
        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, ai_response, re.IGNORECASE)
            for match in matches:
                citation = self._create_citation_from_match(
                    match, transcription, session
                )
                if citation:
                    citations.append(citation)
        
        # セマンティック類似度による引用検索
        semantic_citations = self._find_semantic_citations(
            ai_response, transcription, session
        )
        citations.extend(semantic_citations)
        
        # 重複除去
        unique_citations = self._deduplicate_citations(citations)
        
        logger.info(f"引用抽出完了: {len(unique_citations)}件の引用")
        return unique_citations
    
    def _create_citation_from_match(
        self,
        match: re.Match,
        transcription: str,
        session
    ):
        """
        正規表現マッチから引用を作成
        
        Args:
            match: 正規表現マッチ結果
            transcription: 文字起こし
            session: セッション
        
        Returns:
            Optional: 作成された引用
        """
        # Import Citation at runtime to avoid circular imports
        from app.models.chat import Citation
        
        citation_text = match.group(1) if match.groups() else match.group(0)
        
        # 文字起こし内で該当テキストを検索
        position = self._find_text_position(citation_text, transcription)
        if position is None:
            # 類似テキストを検索
            position, actual_text = self._find_similar_text(citation_text, transcription)
            if position is None:
                return None
            citation_text = actual_text
        
        # タイムスタンプを推定
        timestamp = self._estimate_timestamp(position, transcription, session)
        
        # 信頼度を計算
        confidence = self._calculate_confidence(citation_text, transcription, position)
        
        return Citation(
            text=citation_text,
            start_time=timestamp,
            confidence=confidence,
            context=self._extract_context(position, transcription),
            highlight_start=position,
            highlight_end=position + len(citation_text)
        )
    
    def _find_semantic_citations(
        self,
        ai_response: str,
        transcription: str,
        session
    ):
        """
        セマンティック類似度による引用検索
        
        Args:
            ai_response: AI回答
            transcription: 文字起こし
            session: セッション
        
        Returns:
            List: セマンティック引用リスト
        """
        # 簡易実装：キーワードベース検索
        # 実際の実装では、埋め込みベクトルやBM25を使用
        
        # Import Citation at runtime to avoid circular imports
        from app.models.chat import Citation
        
        citations = []
        
        # AI回答から重要な名詞句を抽出
        important_phrases = self._extract_important_phrases(ai_response)
        
        for phrase in important_phrases:
            if len(phrase) < 5:  # 短すぎる語句は除外
                continue
                
            position = self._find_text_position(phrase, transcription)
            if position is not None:
                timestamp = self._estimate_timestamp(position, transcription, session)
                confidence = self._calculate_confidence(phrase, transcription, position)
                
                # 信頼度が一定以上の場合のみ追加
                if confidence >= 0.7:
                    citation = Citation(
                        text=phrase,
                        start_time=timestamp,
                        confidence=confidence,
                        context=self._extract_context(position, transcription),
                        highlight_start=position,
                        highlight_end=position + len(phrase)
                    )
                    citations.append(citation)
        
        return citations
    
    def _extract_important_phrases(self, text: str) -> List[str]:
        """
        テキストから重要な語句を抽出
        
        Args:
            text: 対象テキスト
        
        Returns:
            List[str]: 重要語句リスト
        """
        # 簡易実装：括弧内のテキストや名詞句を抽出
        phrases = []
        
        # 括弧内のテキスト
        bracket_patterns = [
            r'「([^」]+)」',
            r'『([^』]+)』',
            r'\(([^)]+)\)',
            r'（([^）]+)）',
        ]
        
        for pattern in bracket_patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches)
        
        # その他の重要語句パターン
        important_patterns = [
            r'について\s*([^。]+)',
            r'に関して\s*([^。]+)',
            r'という\s*([^。]+)',
        ]
        
        for pattern in important_patterns:
            matches = re.findall(pattern, text)
            phrases.extend([match.strip() for match in matches])
        
        return list(set(phrases))  # 重複除去
    
    def _find_text_position(self, target_text: str, source_text: str) -> Optional[int]:
        """
        ソーステキスト内での対象テキストの位置を検索
        
        Args:
            target_text: 検索対象テキスト
            source_text: 検索元テキスト
        
        Returns:
            Optional[int]: 見つかった位置（文字インデックス）
        """
        # 完全一致検索
        position = source_text.find(target_text)
        if position != -1:
            return position
        
        # 正規化して検索
        normalized_target = self._normalize_text(target_text)
        normalized_source = self._normalize_text(source_text)
        
        position = normalized_source.find(normalized_target)
        if position != -1:
            # 元のテキストでの位置を計算
            return self._map_normalized_position(position, source_text, normalized_source)
        
        return None
    
    def _find_similar_text(self, target_text: str, source_text: str) -> Tuple[Optional[int], str]:
        """
        類似テキストを検索
        
        Args:
            target_text: 検索対象テキスト
            source_text: 検索元テキスト
        
        Returns:
            Tuple[Optional[int], str]: (位置, 実際のテキスト)
        """
        # 簡易実装：部分文字列マッチング
        target_words = target_text.split()
        best_match = None
        best_position = None
        best_score = 0
        
        # 文章を単語単位で分割してスライディングウィンドウで検索
        source_words = source_text.split()
        
        for i in range(len(source_words) - len(target_words) + 1):
            window = source_words[i:i + len(target_words)]
            similarity = self._calculate_text_similarity(target_words, window)
            
            if similarity > best_score and similarity > 0.6:  # 閾値
                best_score = similarity
                best_match = ' '.join(window)
                # 実際の文字位置を計算
                words_before = source_words[:i]
                best_position = len(' '.join(words_before)) + (1 if words_before else 0)
        
        return best_position, best_match or target_text
    
    def _calculate_text_similarity(self, words1: List[str], words2: List[str]) -> float:
        """
        単語リスト間の類似度を計算
        
        Args:
            words1: 単語リスト1
            words2: 単語リスト2
        
        Returns:
            float: 類似度スコア (0-1)
        """
        if not words1 or not words2:
            return 0.0
        
        # 簡易的なJaccard係数
        set1 = set(self._normalize_text(word) for word in words1)
        set2 = set(self._normalize_text(word) for word in words2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _normalize_text(self, text: str) -> str:
        """
        テキストを正規化
        
        Args:
            text: 対象テキスト
        
        Returns:
            str: 正規化後テキスト
        """
        # 空白文字の正規化
        text = re.sub(r'\s+', ' ', text)
        # 句読点の正規化
        text = re.sub(r'[、。，．]', '', text)
        # 大文字小文字の統一
        text = text.lower()
        return text.strip()
    
    def _map_normalized_position(self, normalized_pos: int, original_text: str, normalized_text: str) -> int:
        """
        正規化されたテキストでの位置を元のテキストでの位置にマッピング
        
        Args:
            normalized_pos: 正規化テキスト内の位置
            original_text: 元のテキスト
            normalized_text: 正規化テキスト
        
        Returns:
            int: 元のテキスト内の位置
        """
        # 簡易実装：文字数の比例から推定
        ratio = len(original_text) / len(normalized_text) if normalized_text else 1
        return int(normalized_pos * ratio)
    
    def _estimate_timestamp(self, position: int, transcription: str, session) -> str:
        """
        テキスト位置からタイムスタンプを推定
        
        Args:
            position: テキスト位置
            transcription: 文字起こし
            session: セッション
        
        Returns:
            str: 推定タイムスタンプ
        """
        # 簡易実装：位置の比例からタイムスタンプを推定
        text_ratio = position / len(transcription) if transcription else 0
        
        # 仮想的な動画時間（実際の実装では動画メタデータから取得）
        estimated_duration_seconds = len(transcription) // 10  # 1秒あたり10文字と仮定
        estimated_time_seconds = int(text_ratio * estimated_duration_seconds)
        
        # HH:MM:SS形式に変換
        hours = estimated_time_seconds // 3600
        minutes = (estimated_time_seconds % 3600) // 60
        seconds = estimated_time_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _calculate_confidence(self, citation_text: str, transcription: str, position: int) -> float:
        """
        引用の信頼度を計算
        
        Args:
            citation_text: 引用テキスト
            transcription: 文字起こし
            position: 位置
        
        Returns:
            float: 信頼度 (0-1)
        """
        confidence = 0.0
        
        # 完全一致の場合は高い信頼度
        actual_text = transcription[position:position + len(citation_text)]
        if actual_text == citation_text:
            confidence += 0.5
        
        # テキストの長さによる信頼度調整
        if len(citation_text) >= 10:
            confidence += 0.3
        elif len(citation_text) >= 5:
            confidence += 0.2
        
        # 文脈の妥当性チェック
        context = self._extract_context(position, transcription)
        if self._is_valid_context(citation_text, context):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _extract_context(self, position: int, transcription: str, context_length: int = 100) -> str:
        """
        引用の前後文脈を抽出
        
        Args:
            position: 引用位置
            transcription: 文字起こし
            context_length: 文脈の長さ
        
        Returns:
            str: 前後文脈
        """
        start = max(0, position - context_length)
        end = min(len(transcription), position + context_length)
        
        context = transcription[start:end]
        
        # 文の境界で切る
        if start > 0:
            first_period = context.find('。')
            if first_period != -1:
                context = context[first_period + 1:]
        
        if end < len(transcription):
            last_period = context.rfind('。')
            if last_period != -1:
                context = context[:last_period + 1]
        
        return context.strip()
    
    def _is_valid_context(self, citation_text: str, context: str) -> bool:
        """
        文脈が妥当かチェック
        
        Args:
            citation_text: 引用テキスト
            context: 文脈
        
        Returns:
            bool: 妥当性
        """
        # 簡易チェック：引用テキストが文脈に含まれているか
        return citation_text in context
    
    def _deduplicate_citations(self, citations):
        """
        重複する引用を除去
        
        Args:
            citations: 引用リスト
        
        Returns:
            List: 重複除去後の引用リスト
        """
        unique_citations = []
        seen_texts = set()
        
        for citation in citations:
            # テキストの正規化で重複チェック
            normalized_text = self._normalize_text(citation.text)
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_citations.append(citation)
        
        # 信頼度でソート
        unique_citations.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_citations
    
    def create_highlight_info(self, citation, transcription: str) -> Dict:
        """
        ハイライト情報を作成
        
        Args:
            citation: 引用情報
            transcription: 文字起こし
        
        Returns:
            Dict: ハイライト情報
        """
        return {
            "citation_id": citation.citation_id,
            "start_position": citation.highlight_start,
            "end_position": citation.highlight_end,
            "highlighted_text": citation.text,
            "timestamp": citation.start_time,
            "confidence": citation.confidence,
            "context": citation.context,
            "created_at": datetime.now().isoformat()
        }

# グローバルな引用サービスインスタンス
citation_service = CitationService()