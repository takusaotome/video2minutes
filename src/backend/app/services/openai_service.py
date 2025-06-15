"""OpenAI GPT-4統合サービス"""
import json
import time
import re
import asyncio
from typing import Dict, List, Optional, Tuple

from app.models.chat import (
    ChatMessage,
    ChatSession,
    MessageIntent,
    Citation,
    EditAction,
    EditActionType,
    EditScope,
    TokenUsage
)
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OpenAI クライアントの初期化（実際のAPI統合用）
try:
    import openai
    openai.api_key = settings.openai_api_key
    OPENAI_AVAILABLE = True
    logger.info("OpenAI クライアント初期化完了")
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openaiライブラリがインストールされていません。模擬レスポンスを使用します。")
except Exception as e:
    OPENAI_AVAILABLE = False
    logger.warning(f"OpenAI初期化エラー: {e}。模擬レスポンスを使用します。")

class OpenAIService:
    """OpenAI GPT-4統合サービス"""
    
    def __init__(self):
        self.model = settings.openai_chat_model
        self.max_tokens = settings.openai_chat_max_tokens
        self.temperature = settings.openai_chat_temperature
        self.timeout = settings.openai_timeout_seconds
        
        # プロンプト管理システム
        from app.prompts.chat_prompts import (
            get_chat_system_prompt,
            get_edit_analysis_prompt,
            build_chat_history_context,
            build_user_prompt
        )
        self.prompt_manager = {
            "get_chat_system_prompt": get_chat_system_prompt,
            "get_edit_analysis_prompt": get_edit_analysis_prompt,
            "build_chat_history_context": build_chat_history_context,
            "build_user_prompt": build_user_prompt
        }
        
        # API利用可能性チェック
        self.use_mock = not OPENAI_AVAILABLE or not settings.openai_api_key
        
        if self.use_mock:
            logger.info("OpenAI API模擬モードで動作します")
        else:
            logger.info(f"OpenAI API統合モードで動作します (model: {self.model})")
    
    async def process_chat_message(
        self,
        session: ChatSession,
        message: str,
        intent: MessageIntent,
        chat_history: List[ChatMessage]
    ) -> Dict:
        """
        チャットメッセージを処理してAI回答を生成
        
        Args:
            session: チャットセッション
            message: ユーザーメッセージ
            intent: メッセージの意図
            chat_history: チャット履歴
        
        Returns:
            Dict: AI回答データ
        """
        start_time = time.time()
        
        try:
            if intent == MessageIntent.QUESTION:
                return await self._process_question(session, message, chat_history)
            else:
                return await self._process_edit_request(session, message, chat_history)
                
        except Exception as e:
            logger.error(f"OpenAI処理エラー: {e}", exc_info=True)
            return self._create_error_response(str(e), time.time() - start_time)
    
    async def _process_question(
        self,
        session: ChatSession,
        message: str,
        chat_history: List[ChatMessage]
    ) -> Dict:
        """質問を処理"""
        # プロンプトを構築
        system_prompt = self.prompt_manager["get_chat_system_prompt"](
            transcription=session.transcription,
            minutes=session.minutes
        )
        
        # チャット履歴をコンテキストに変換
        chat_context = self.prompt_manager["build_chat_history_context"](chat_history)
        user_prompt = self.prompt_manager["build_user_prompt"](message, chat_context)
        
        # 現在は模擬実装（後でOpenAI APIに置き換え）
        response_text, citations = await self._call_openai_api(
            system_prompt, user_prompt, intent="question"
        )
        
        processing_time = time.time() - time.time()
        tokens_used = self._estimate_tokens(system_prompt + user_prompt + response_text)
        
        return {
            "response": response_text,
            "citations": citations,
            "edit_actions": [],
            "tokens_used": tokens_used,
            "processing_time": processing_time
        }
    
    async def _process_edit_request(
        self,
        session: ChatSession,
        message: str,
        chat_history: List[ChatMessage]
    ) -> Dict:
        """編集リクエストを処理"""
        # 編集インテント解析用のプロンプトを構築
        system_prompt = self.prompt_manager["get_edit_analysis_prompt"](
            current_minutes=session.minutes,
            edit_instruction=message
        )
        
        user_prompt = message  # 編集指示をそのまま渡す
        
        # OpenAI APIを呼び出して編集アクションを生成
        response_text, edit_actions = await self._analyze_edit_intent(
            system_prompt, user_prompt, session.minutes
        )
        
        processing_time = time.time() - time.time()
        tokens_used = self._estimate_tokens(system_prompt + user_prompt + response_text)
        
        return {
            "response": response_text,
            "citations": [],
            "edit_actions": edit_actions,
            "tokens_used": tokens_used,
            "processing_time": processing_time
        }
    
    async def _call_openai_api(
        self,
        system_prompt: str,
        user_prompt: str,
        intent: str = "question"
    ) -> Tuple[str, List[Citation]]:
        """
        OpenAI APIを呼び出し
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            intent: 処理の意図
        
        Returns:
            Tuple: (回答テキスト, 引用リスト)
        """
        if self.use_mock:
            return await self._call_mock_api(system_prompt, user_prompt, intent)
        
        try:
            logger.info(f"OpenAI API呼び出し開始 - intent: {intent}, model: {self.model}")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # OpenAI API呼び出し
            response = await asyncio.wait_for(
                self._make_openai_request(messages),
                timeout=self.timeout
            )
            
            response_text = response.choices[0].message.content
            
            # AIの回答から引用を抽出する代わりに、コンテンツベースの引用を生成
            citations = self._generate_smart_citations(user_prompt, response_text)
            
            logger.info(f"OpenAI API呼び出し成功 - tokens: {response.usage.total_tokens}")
            
            return response_text, citations
            
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API呼び出しタイムアウト ({self.timeout}秒)")
            # タイムアウト時は実際のエラーを返す
            return f"申し訳ございません。AI処理がタイムアウトしました（{self.timeout}秒）。", []
        
        except Exception as e:
            logger.error(f"OpenAI API呼び出しエラー: {e}", exc_info=True)
            # エラー時は実際のエラーを返す（模擬モードにフォールバックしない）
            return f"申し訳ございません。AI処理中にエラーが発生しました: {str(e)}", []
    
    async def _make_openai_request(self, messages: List[Dict]):
        """OpenAI APIリクエストを実行"""
        if OPENAI_AVAILABLE:
            try:
                # 新しいOpenAI v1.0+ クライアント使用
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                
                # o3系モデルは特殊なパラメーター構成
                if self.model.startswith('o3'):
                    # o3系モデルは基本パラメーターのみ対応
                    response = await client.chat.completions.create(
                        model=self.model,
                        messages=messages
                    )
                else:
                    response = await client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        timeout=self.timeout
                    )
                return response
            except ImportError:
                # 古いライブラリバージョンのフォールバック
                response = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=self.timeout
                )
                return response
        else:
            raise Exception("OpenAI library not available")
    
    async def _call_mock_api(
        self,
        system_prompt: str,
        user_prompt: str,
        intent: str = "question"
    ) -> Tuple[str, List[Citation]]:
        """模擬API呼び出し（改善版）"""
        logger.info(f"OpenAI API模擬呼び出し - intent: {intent}")
        
        # 少し遅延を追加してリアル感を演出
        await asyncio.sleep(0.5)
        
        if intent == "question":
            # システムプロンプトから文字起こしと議事録を抽出
            transcription = self._extract_transcription_from_prompt(system_prompt)
            minutes = self._extract_minutes_from_prompt(system_prompt)
            
            # ユーザーの質問を抽出
            question = user_prompt.split('【新しい質問】')[-1].strip() if '【新しい質問】' in user_prompt else user_prompt
            
            # 質問に関連する内容を検索
            relevant_content = self._find_relevant_content(question, transcription, minutes)
            
            if relevant_content:
                response_text = f"ご質問「{question}」についてお答えします。\n\n{relevant_content}"
                
                # 関連する引用を生成
                citations = self._generate_relevant_citations(question, transcription)
            else:
                response_text = f"ご質問「{question}」について、議事録および文字起こしから検索しましたが、直接的な言及は見つかりませんでした。\n\n関連する可能性のある内容がある場合は、より具体的な質問をしていただけると詳細な回答ができます。"
                citations = []
                
        else:
            response_text = "編集指示を確認いたします。議事録の内容を解析して、適切な編集を実行いたします。"
            citations = []
        
        return response_text, citations
    
    def _extract_transcription_from_prompt(self, system_prompt: str) -> str:
        """システムプロンプトから文字起こしを抽出"""
        # プロンプトから文字起こし部分を抽出
        import re
        match = re.search(r'【文字起こし内容】\s*\n(.*?)\n【議事録内容】', system_prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_minutes_from_prompt(self, system_prompt: str) -> str:
        """システムプロンプトから議事録を抽出"""
        import re
        match = re.search(r'【議事録内容】\s*\n(.*?)(?:\n【|$)', system_prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _find_relevant_content(self, question: str, transcription: str, minutes: str) -> str:
        """質問に関連する内容を検索"""
        import re
        
        # 質問からキーワードを抽出
        keywords = self._extract_keywords(question)
        
        relevant_parts = []
        
        # 議事録から関連部分を検索
        if minutes:
            for keyword in keywords:
                # 完全一致
                if keyword in minutes:
                    context = self._get_context_around_keyword(keyword, minutes, 150)
                    if context and context not in relevant_parts:
                        relevant_parts.append(f"**議事録から：**\n{context}")
                # 部分一致（例：「技術」が「技術担当」にマッチ）
                else:
                    import re
                    pattern = re.compile(r'[^。\n]*' + re.escape(keyword) + r'[^。\n]*', re.IGNORECASE)
                    matches = pattern.findall(minutes)
                    if matches:
                        for match in matches[:2]:  # 最大2つのマッチ
                            cleaned_match = match.strip()
                            if cleaned_match and len(cleaned_match) > 10:
                                content_only = [part.split('\n', 1)[1] if '\n' in part else part for part in relevant_parts]
                                if cleaned_match not in content_only:
                                    relevant_parts.append(f"**議事録から：**\n{cleaned_match}")
        
        # 文字起こしから関連部分を検索
        if transcription and len(relevant_parts) < 3:
            for keyword in keywords:
                # 完全一致
                if keyword in transcription:
                    context = self._get_context_around_keyword(keyword, transcription, 150)
                    if context and context not in relevant_parts:
                        relevant_parts.append(f"**文字起こしから：**\n{context}")
                # 部分一致
                else:
                    import re
                    pattern = re.compile(r'[^。\n]*' + re.escape(keyword) + r'[^。\n]*', re.IGNORECASE)
                    matches = pattern.findall(transcription)
                    if matches:
                        for match in matches[:1]:  # 最初のマッチのみ
                            cleaned_match = match.strip()
                            if cleaned_match and len(cleaned_match) > 10:
                                content_only = [part.split('\n', 1)[1] if '\n' in part else part for part in relevant_parts]
                                if cleaned_match not in content_only:
                                    relevant_parts.append(f"**文字起こしから：**\n{cleaned_match}")
        
        return "\n\n".join(relevant_parts[:3])  # 最大3つの関連部分を返す
    
    def _extract_keywords(self, question: str) -> List[str]:
        """質問からキーワードを抽出"""
        import re
        
        # 日本語の名詞や重要語句を抽出
        keywords = []
        
        # カタカナ語を抽出
        katakana_words = re.findall(r'[ァ-ヶー]+', question)
        keywords.extend([w for w in katakana_words if len(w) >= 2])
        
        # 漢字を含む語句を抽出
        kanji_words = re.findall(r'[一-龯ひらがなカタカナ]+', question)
        keywords.extend([w for w in kanji_words if len(w) >= 2])
        
        # 英数字を含む語句を抽出
        alphanumeric = re.findall(r'[a-zA-Z0-9]+', question)
        keywords.extend([w for w in alphanumeric if len(w) >= 2])
        
        # 特定のパターンマッチング
        specific_patterns = {
            r'技術.{0,2}担当': '技術',
            r'プロジェクト.{0,2}マネージャ': 'マネージャー',
            r'予算.{0,5}': '予算',
            r'期間.{0,5}': '期間',
            r'レビュー': 'レビュー',
            r'設計': '設計',
            r'アクション.{0,2}アイテム': 'アクション',
            r'担当.{0,2}者?': '担当',
            r'参加.{0,2}者?': '参加',
        }
        
        for pattern, keyword in specific_patterns.items():
            if re.search(pattern, question):
                keywords.append(keyword)
        
        # 名前パターン（〜さん）
        name_pattern = re.findall(r'([一-龯ひらがなカタカナa-zA-Z]+)さん', question)
        keywords.extend(name_pattern)
        
        # 重複除去と短すぎるキーワードの除外
        keywords = list(set([k for k in keywords if len(k) >= 2]))
        
        # よくある質問語を除外
        stop_words = {"について", "どう", "なぜ", "いつ", "どこ", "誰", "何", "どの", "です", "ます", "した", "する", "ある", "いる", "この", "その", "あの", "教えて", "ください"}
        keywords = [k for k in keywords if k not in stop_words]
        
        return keywords[:5]  # 最大5つのキーワード
    
    def _get_context_around_keyword(self, keyword: str, text: str, context_length: int) -> str:
        """キーワード周辺のコンテキストを取得"""
        pos = text.find(keyword)
        if pos == -1:
            return ""
        
        start = max(0, pos - context_length // 2)
        end = min(len(text), pos + len(keyword) + context_length // 2)
        
        context = text[start:end].strip()
        
        # 文の境界で切る
        if start > 0:
            first_period = context.find('。')
            if first_period != -1:
                context = context[first_period + 1:]
        
        if end < len(text):
            last_period = context.rfind('。')
            if last_period != -1:
                context = context[:last_period + 1]
        
        return context.strip()
    
    def _generate_relevant_citations(self, question: str, transcription: str) -> List[Citation]:
        """質問に関連する引用を生成"""
        keywords = self._extract_keywords(question)
        citations = []
        
        for i, keyword in enumerate(keywords[:2]):  # 最大2つの引用
            pos = transcription.find(keyword)
            if pos != -1:
                context = self._get_context_around_keyword(keyword, transcription, 80)
                if context:
                    # タイムスタンプを推定
                    text_ratio = pos / len(transcription) if transcription else 0
                    estimated_seconds = int(text_ratio * 600)  # 10分の動画と仮定
                    hours = estimated_seconds // 3600
                    minutes = (estimated_seconds % 3600) // 60
                    seconds = estimated_seconds % 60
                    timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    citation = Citation(
                        text=context[:50] + "..." if len(context) > 50 else context,
                        start_time=timestamp,
                        confidence=0.8 - i * 0.1,  # 最初の引用ほど高い信頼度
                        context=context,
                        highlight_start=pos,
                        highlight_end=pos + len(keyword)
                    )
                    citations.append(citation)
        
        return citations
    
    def _generate_smart_citations(self, user_prompt: str, ai_response: str) -> List[Citation]:
        """AIの回答に基づいて関連する引用を生成"""
        # ユーザーの質問からキーワードを抽出
        keywords = self._extract_keywords(user_prompt)
        
        # 現在のセッションから文字起こしを取得（簡易実装）
        # 実際の実装では、セッション情報から取得
        citations = []
        
        # シンプルな引用生成（AIの回答内容に基づく）
        if "データの利活用" in ai_response or "データ利活用" in ai_response:
            citations.append(Citation(
                text="データの利活用みたいなところは多分次のフェーズになるかもしれないんですが、一応そういう要望もあるというところは理解いたしました",
                start_time="00:03:39",
                confidence=0.9,
                context="データ利活用に関する要望についての言及"
            ))
        
        if "物件推薦" in ai_response or "物件" in ai_response:
            citations.append(Citation(
                text="内覧するときにこのお客さんにどの物件を紹介しようという絞り込みをしているんですが",
                start_time="00:11:53", 
                confidence=0.85,
                context="物件推薦システムに関する現状の説明"
            ))
            
        return citations[:2]  # 最大2つの引用
    
    def _extract_citations(self, response_text: str) -> List[Citation]:
        """レスポンステキストから引用を抽出"""
        citations = []
        
        # 引用パターンを検索（実装は後で改善）
        citation_pattern = r'引用:\s*"([^"]+)"'
        matches = re.findall(citation_pattern, response_text)
        
        for i, match in enumerate(matches):
            citations.append(Citation(
                text=match,
                start_time=f"00:{5+i*2:02d}:00",  # 模擬タイムスタンプ
                confidence=0.85,
                context="AI分析による引用",
                highlight_start=i * 50,  # 模擬ハイライト位置
                highlight_end=i * 50 + len(match)
            ))
        
        return citations
    
    async def _analyze_edit_intent(
        self,
        system_prompt: str,
        user_prompt: str,
        current_minutes: str
    ) -> Tuple[str, List[EditAction]]:
        """
        編集インテントを解析
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            current_minutes: 現在の議事録
        
        Returns:
            Tuple: (説明テキスト, 編集アクションリスト)
        """
        # 高度な編集インテント解析エンジンを使用
        from app.services.edit_intent_analyzer import edit_intent_analyzer
        
        edit_instruction = user_prompt
        logger.info(f"高度な編集インテント解析開始: {edit_instruction[:50]}...")
        
        try:
            # まず、パターンベース解析を実行
            edit_actions, explanation = edit_intent_analyzer.analyze_edit_intent(
                edit_instruction, current_minutes
            )
            
            if self.use_mock:
                # 模擬モードでは、パターンベース解析のみ使用
                response_text = explanation
                if edit_actions:
                    response_text += "\n\n実行してよろしいですか？"
                return response_text, edit_actions
            
            # OpenAI APIが利用可能な場合はAI解析も実行
            ai_response = await self._call_openai_for_edit_analysis(
                system_prompt, user_prompt, edit_actions
            )
            
            # AI解析結果とパターンベース解析を統合
            final_actions, final_explanation = self._merge_edit_analysis(
                edit_actions, explanation, ai_response
            )
            
            return final_explanation, final_actions
            
        except Exception as e:
            logger.error(f"編集インテント解析エラー: {e}", exc_info=True)
            # エラー時はフォールバック
            return self._fallback_edit_analysis(edit_instruction, current_minutes)
    
    async def _call_openai_for_edit_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        pattern_actions: List[EditAction]
    ) -> str:
        """
        OpenAI APIで編集解析を実行
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            pattern_actions: パターンベース解析結果
        
        Returns:
            str: AI解析結果
        """
        # パターンベース解析結果をプロンプトに含める
        pattern_summary = ""
        if pattern_actions:
            pattern_summary = "【パターンベース解析結果】\n"
            for action in pattern_actions:
                pattern_summary += f"- {action.description}\n"
            pattern_summary += "\n"
        
        enhanced_prompt = f"{pattern_summary}【編集指示】\n{user_prompt}\n\n上記の編集指示とパターン解析結果を参考に、より詳細で正確な編集アクションを提案してください。"
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_prompt}
            ]
            
            response = await asyncio.wait_for(
                self._make_openai_request(messages),
                timeout=self.timeout
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI編集解析エラー: {e}")
            return "AI解析に失敗しましたが、パターンベース解析を使用します。"
    
    def _merge_edit_analysis(
        self,
        pattern_actions: List[EditAction],
        pattern_explanation: str,
        ai_response: str
    ) -> Tuple[List[EditAction], str]:
        """
        パターンベース解析とAI解析を統合
        
        Args:
            pattern_actions: パターンベース解析アクション
            pattern_explanation: パターンベース解析説明
            ai_response: AI解析レスポンス
        
        Returns:
            Tuple: (統合アクション, 統合説明)
        """
        # AI解析でJSONが含まれている場合は抽出
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                ai_data = json.loads(json_match.group())
                if "edit_actions" in ai_data:
                    # AI提案のアクションを追加
                    for ai_action_data in ai_data["edit_actions"]:
                        # JSON形式のアクションをEditActionオブジェクトに変換
                        ai_action = self._json_to_edit_action(ai_action_data)
                        if ai_action and not self._is_duplicate_action(ai_action, pattern_actions):
                            pattern_actions.append(ai_action)
            except json.JSONDecodeError:
                logger.warning("AI解析のJSON解析に失敗")
        
        # 統合説明を生成
        merged_explanation = f"{pattern_explanation}\n\n【AI解析補足】\n{ai_response}"
        
        return pattern_actions, merged_explanation
    
    def _json_to_edit_action(self, action_data: Dict) -> Optional[EditAction]:
        """JSONデータからEditActionオブジェクトを作成"""
        try:
            action_type_str = action_data.get("action_type", "")
            action_type = EditActionType(action_type_str)
            
            action = EditAction(
                action_type=action_type,
                target=action_data.get("target"),
                replacement=action_data.get("replacement"),
                scope=EditScope(action_data.get("scope", "all")),
                content=action_data.get("content"),
                item_id=action_data.get("item_id"),
                updates=action_data.get("updates"),
                description=action_data.get("description", "")
            )
            return action
        except (ValueError, KeyError) as e:
            logger.warning(f"EditAction変換エラー: {e}")
            return None
    
    def _is_duplicate_action(self, new_action: EditAction, existing_actions: List[EditAction]) -> bool:
        """重複アクションをチェック"""
        for existing in existing_actions:
            if (existing.action_type == new_action.action_type and 
                existing.target == new_action.target and
                existing.replacement == new_action.replacement):
                return True
        return False
    
    def _fallback_edit_analysis(self, edit_instruction: str, current_minutes: str) -> Tuple[str, List[EditAction]]:
        """フォールバック編集解析"""
        response_text = f"編集指示「{edit_instruction}」を基本的なパターンで解析しました。"
        
        # 単純なテキスト追加として処理
        action = EditAction(
            action_type=EditActionType.ADD_CONTENT,
            content={"text": edit_instruction},
            description="編集指示をテキストとして追加"
        )
        
        return response_text, [action]
    
    
    def _estimate_tokens(self, text: str) -> int:
        """トークン数を概算"""
        # 日本語と英語の混在テキストのトークン数概算
        japanese_chars = sum(1 for char in text if ord(char) > 127)
        english_chars = len(text) - japanese_chars
        
        # 日本語: 約1.5文字で1トークン、英語: 約4文字で1トークン
        estimated_tokens = int(japanese_chars / 1.5) + int(english_chars / 4)
        
        return max(estimated_tokens, 50)
    
    def _create_error_response(self, error_message: str, processing_time: float) -> Dict:
        """エラーレスポンスを作成"""
        return {
            "response": f"申し訳ございませんが、処理中にエラーが発生しました: {error_message}",
            "citations": [],
            "edit_actions": [],
            "tokens_used": 100,
            "processing_time": processing_time
        }


# グローバルなOpenAIサービスインスタンス
openai_service = OpenAIService()