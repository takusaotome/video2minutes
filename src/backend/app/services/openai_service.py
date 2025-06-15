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
            
            # 引用を抽出
            citations = self._extract_citations(response_text)
            
            logger.info(f"OpenAI API呼び出し成功 - tokens: {response.usage.total_tokens}")
            
            return response_text, citations
            
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API呼び出しタイムアウト ({self.timeout}秒)")
            return await self._call_mock_api(system_prompt, user_prompt, intent)
        
        except Exception as e:
            logger.error(f"OpenAI API呼び出しエラー: {e}", exc_info=True)
            return await self._call_mock_api(system_prompt, user_prompt, intent)
    
    async def _make_openai_request(self, messages: List[Dict]):
        """OpenAI APIリクエストを実行"""
        if OPENAI_AVAILABLE:
            try:
                # 新しいOpenAI v1.0+ クライアント使用
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                
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
        """模擬API呼び出し"""
        logger.info(f"OpenAI API模擬呼び出し - intent: {intent}")
        
        # 少し遅延を追加してリアル感を演出
        await asyncio.sleep(0.5)
        
        if intent == "question":
            question = user_prompt.split('【新しい質問】')[-1].strip() if '【新しい質問】' in user_prompt else user_prompt
            response_text = f"ご質問「{question}」について、文字起こし内容を確認いたします。\n\n申し訳ございませんが、現在OpenAI APIとの統合を準備中です。実際のAI回答は近日中に利用可能になります。\n\n模擬モードでは詳細な回答ができませんが、システムは正常に動作しています。"
            
            # 模擬引用を生成
            citations = [
                Citation(
                    text="会議の重要な発言例（模擬データ）",
                    start_time="00:05:30",
                    confidence=0.92,
                    context="議題説明時の発言として参照",
                    highlight_start=150,
                    highlight_end=170
                )
            ]
        else:
            response_text = "編集指示を確認いたします。OpenAI統合完了後、より精密な編集分析が可能になります。現在は基本的なパターンマッチングで編集を実行します。"
            citations = []
        
        return response_text, citations
    
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