"""OpenAIサービスのテスト"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.openai_service import OpenAIService, openai_service
from app.models.chat import (
    ChatSession,
    ChatMessage,
    MessageIntent,
    Citation,
    EditAction,
    EditActionType,
    EditScope
)


class TestOpenAIService:
    """OpenAIサービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.openai_service = OpenAIService()
        self.sample_session = Mock(spec=ChatSession)
        self.sample_session.transcription = "会議の文字起こし内容です。プロジェクトについて議論しました。"
        self.sample_session.minutes = "# 会議議事録\n\n## プロジェクトについて\n\n議論した内容"

    def test_initialization(self):
        """初期化テスト"""
        service = OpenAIService()
        assert service.model is not None
        assert service.max_tokens > 0
        assert service.temperature >= 0
        assert service.timeout > 0
        assert hasattr(service, 'prompt_manager')
        assert hasattr(service, 'use_mock')

    @pytest.mark.asyncio
    async def test_process_chat_message_question(self):
        """質問処理テスト"""
        message = "プロジェクトの進捗はどうですか？"
        intent = MessageIntent.QUESTION
        chat_history = []
        
        with patch.object(self.openai_service, '_process_question') as mock_process:
            mock_process.return_value = {
                "response": "プロジェクトは順調に進んでいます",
                "citations": [],
                "edit_actions": [],
                "tokens_used": 100,
                "processing_time": 1.5
            }
            
            result = await self.openai_service.process_chat_message(
                self.sample_session, message, intent, chat_history
            )
            
            assert "response" in result
            assert "citations" in result
            assert "edit_actions" in result
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_message_edit(self):
        """編集処理テスト"""
        message = "議事録にアクションアイテムを追加してください"
        intent = MessageIntent.EDIT_REQUEST
        chat_history = []
        
        with patch.object(self.openai_service, '_process_edit_request') as mock_process:
            mock_process.return_value = {
                "response": "アクションアイテムを追加します",
                "citations": [],
                "edit_actions": [],
                "tokens_used": 150,
                "processing_time": 2.0
            }
            
            result = await self.openai_service.process_chat_message(
                self.sample_session, message, intent, chat_history
            )
            
            assert "response" in result
            assert "edit_actions" in result
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_message_error(self):
        """エラー処理テスト"""
        message = "テストメッセージ"
        intent = MessageIntent.QUESTION
        chat_history = []
        
        with patch.object(self.openai_service, '_process_question') as mock_process:
            mock_process.side_effect = Exception("テストエラー")
            
            result = await self.openai_service.process_chat_message(
                self.sample_session, message, intent, chat_history
            )
            
            assert "処理中にエラーが発生しました" in result["response"]
            assert result["citations"] == []
            assert result["edit_actions"] == []

    @pytest.mark.asyncio
    async def test_process_question(self):
        """質問処理の詳細テスト"""
        message = "プロジェクトについて教えて"
        chat_history = []
        
        # prompt_managerをモック化
        mock_prompts = {
            "get_chat_system_prompt": Mock(return_value="システムプロンプト"),
            "build_chat_history_context": Mock(return_value="チャット履歴"),
            "build_user_prompt": Mock(return_value="ユーザープロンプト")
        }
        self.openai_service.prompt_manager = mock_prompts
        
        with patch.object(self.openai_service, '_call_openai_api') as mock_api:
            mock_api.return_value = ("テスト回答", [])
            
            result = await self.openai_service._process_question(
                self.sample_session, message, chat_history
            )
            
            assert result["response"] == "テスト回答"
            assert isinstance(result["citations"], list)
            mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_edit_request(self):
        """編集リクエスト処理テスト"""
        message = "アクションアイテムを追加"
        chat_history = []
        
        mock_prompts = {
            "get_edit_analysis_prompt": Mock(return_value="編集プロンプト")
        }
        self.openai_service.prompt_manager = mock_prompts
        
        with patch.object(self.openai_service, '_analyze_edit_intent') as mock_analyze:
            mock_analyze.return_value = ("編集分析結果", [])
            
            result = await self.openai_service._process_edit_request(
                self.sample_session, message, chat_history
            )
            
            assert result["response"] == "編集分析結果"
            assert isinstance(result["edit_actions"], list)
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_mock_api_question(self):
        """模擬API呼び出し（質問）テスト"""
        system_prompt = "【文字起こし内容】\nテスト文字起こし\n【議事録内容】\nテスト議事録"
        user_prompt = "【新しい質問】テストについて教えて"
        
        self.openai_service.use_mock = True
        
        with patch.object(self.openai_service, '_find_relevant_content') as mock_find:
            mock_find.return_value = "関連コンテンツ"
            
            response_text, citations = await self.openai_service._call_mock_api(
                system_prompt, user_prompt, "question"
            )
            
            assert "テストについて教えて" in response_text
            assert "関連コンテンツ" in response_text
            assert isinstance(citations, list)

    @pytest.mark.asyncio
    async def test_call_mock_api_edit(self):
        """模擬API呼び出し（編集）テスト"""
        system_prompt = "編集システムプロンプト"
        user_prompt = "編集指示"
        
        self.openai_service.use_mock = True
        
        response_text, citations = await self.openai_service._call_mock_api(
            system_prompt, user_prompt, "edit"
        )
        
        assert "編集指示を確認" in response_text
        assert isinstance(citations, list)

    def test_extract_transcription_from_prompt(self):
        """プロンプトからの文字起こし抽出テスト"""
        system_prompt = """
        【文字起こし内容】
        これは文字起こしの内容です。
        会議で話された内容が記録されています。
        【議事録内容】
        議事録の内容
        """
        
        transcription = self.openai_service._extract_transcription_from_prompt(system_prompt)
        
        assert "これは文字起こしの内容です" in transcription
        assert "会議で話された内容" in transcription

    def test_extract_minutes_from_prompt(self):
        """プロンプトからの議事録抽出テスト"""
        system_prompt = """
        【文字起こし内容】
        文字起こし内容
        【議事録内容】
        # 会議議事録
        ## 議題
        プロジェクトについて
        """
        
        minutes = self.openai_service._extract_minutes_from_prompt(system_prompt)
        
        assert "# 会議議事録" in minutes
        assert "プロジェクトについて" in minutes

    def test_extract_keywords(self):
        """キーワード抽出テスト"""
        question = "プロジェクトの技術担当者について教えてください"
        
        keywords = self.openai_service._extract_keywords(question)
        
        assert "プロジェクト" in keywords
        assert "技術" in keywords
        assert len(keywords) <= 5

    def test_extract_keywords_katakana(self):
        """カタカナキーワード抽出テスト"""
        question = "システムのパフォーマンステストについて"
        
        keywords = self.openai_service._extract_keywords(question)
        
        assert "システム" in keywords
        assert "パフォーマンス" in keywords
        assert "テスト" in keywords

    def test_find_relevant_content_with_match(self):
        """関連コンテンツ検索（マッチあり）テスト"""
        question = "プロジェクトについて"
        transcription = "プロジェクトの進捗は良好です。技術的な課題もありません。"
        minutes = "# プロジェクト会議\n\n進捗報告を行いました。"
        
        content = self.openai_service._find_relevant_content(question, transcription, minutes)
        
        assert "プロジェクト" in content
        assert len(content) > 0

    def test_find_relevant_content_no_match(self):
        """関連コンテンツ検索（マッチなし）テスト"""
        question = "存在しないトピック"
        transcription = "プロジェクトの話"
        minutes = "会議の議事録"
        
        content = self.openai_service._find_relevant_content(question, transcription, minutes)
        
        # マッチしない場合は空文字列が返される
        assert isinstance(content, str)

    def test_get_context_around_keyword(self):
        """キーワード周辺コンテキスト取得テスト"""
        keyword = "プロジェクト"
        text = "今日はプロジェクトの進捗について話し合います。多くの課題がありますが順調です。"
        
        context = self.openai_service._get_context_around_keyword(keyword, text, 50)
        
        assert "プロジェクト" in context
        assert len(context) > 0

    def test_generate_relevant_citations(self):
        """関連引用生成テスト"""
        question = "プロジェクトについて"
        transcription = "プロジェクトの進捗は良好です。技術的な問題は解決済みです。"
        
        citations = self.openai_service._generate_relevant_citations(question, transcription)
        
        assert isinstance(citations, list)
        for citation in citations:
            assert hasattr(citation, 'text')
            assert hasattr(citation, 'start_time')
            assert hasattr(citation, 'confidence')

    def test_generate_smart_citations(self):
        """スマート引用生成テスト"""
        user_prompt = "データの利活用について"
        ai_response = "データの利活用に関する要望があります。"
        
        citations = self.openai_service._generate_smart_citations(user_prompt, ai_response)
        
        assert isinstance(citations, list)
        assert len(citations) <= 2

    def test_extract_citations(self):
        """引用抽出テスト"""
        response_text = '引用: "これは重要な発言です" という内容がありました。'
        
        citations = self.openai_service._extract_citations(response_text)
        
        assert isinstance(citations, list)

    @pytest.mark.asyncio
    async def test_analyze_edit_intent_mock_mode(self):
        """編集インテント解析（模擬モード）テスト"""
        system_prompt = "編集システムプロンプト"
        user_prompt = "アクションアイテムを追加"
        current_minutes = "# 議事録\n\n内容"
        
        self.openai_service.use_mock = True
        
        with patch('app.services.edit_intent_analyzer.edit_intent_analyzer') as mock_analyzer:
            mock_action = Mock(spec=EditAction)
            mock_analyzer.analyze_edit_intent.return_value = ([mock_action], "編集説明")
            
            response_text, edit_actions = await self.openai_service._analyze_edit_intent(
                system_prompt, user_prompt, current_minutes
            )
            
            assert "編集説明" in response_text
            assert len(edit_actions) == 1
            mock_analyzer.analyze_edit_intent.assert_called_once()

    def test_estimate_tokens(self):
        """トークン数推定テスト"""
        text = "これは日本語のテストです。This is English text."
        
        tokens = self.openai_service._estimate_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens >= 50

    def test_create_error_response(self):
        """エラーレスポンス作成テスト"""
        error_message = "テストエラー"
        processing_time = 1.5
        
        response = self.openai_service._create_error_response(error_message, processing_time)
        
        assert "処理中にエラーが発生しました" in response["response"]
        assert "テストエラー" in response["response"]
        assert response["citations"] == []
        assert response["edit_actions"] == []
        assert response["tokens_used"] == 100
        assert response["processing_time"] == processing_time

    def test_json_to_edit_action(self):
        """JSON→EditAction変換テスト"""
        action_data = {
            "action_type": "add_content",
            "target": "議事録",
            "content": {"text": "新しい内容"},
            "description": "コンテンツ追加"
        }
        
        action = self.openai_service._json_to_edit_action(action_data)
        
        if action:  # 変換が成功した場合
            assert action.action_type == EditActionType.ADD_CONTENT
            assert action.description == "コンテンツ追加"

    def test_json_to_edit_action_invalid(self):
        """無効なJSON→EditAction変換テスト"""
        action_data = {
            "action_type": "invalid_type",
            "target": None
        }
        
        action = self.openai_service._json_to_edit_action(action_data)
        
        assert action is None

    def test_is_duplicate_action(self):
        """重複アクションチェックテスト"""
        action1 = Mock(spec=EditAction)
        action1.action_type = EditActionType.ADD_CONTENT
        action1.target = "議事録"
        action1.replacement = None
        
        action2 = Mock(spec=EditAction)
        action2.action_type = EditActionType.ADD_CONTENT
        action2.target = "議事録"
        action2.replacement = None
        
        is_duplicate = self.openai_service._is_duplicate_action(action2, [action1])
        
        assert is_duplicate

    def test_is_duplicate_action_different(self):
        """異なるアクションチェックテスト"""
        action1 = Mock(spec=EditAction)
        action1.action_type = EditActionType.ADD_CONTENT
        action1.target = "議事録"
        action1.replacement = None
        
        action2 = Mock(spec=EditAction)
        action2.action_type = EditActionType.REPLACE_TEXT
        action2.target = "別のターゲット"
        action2.replacement = "置換テキスト"
        
        is_duplicate = self.openai_service._is_duplicate_action(action2, [action1])
        
        assert not is_duplicate

    def test_fallback_edit_analysis(self):
        """フォールバック編集解析テスト"""
        edit_instruction = "テスト編集指示"
        current_minutes = "現在の議事録"
        
        response_text, edit_actions = self.openai_service._fallback_edit_analysis(
            edit_instruction, current_minutes
        )
        
        assert "テスト編集指示" in response_text
        assert len(edit_actions) == 1
        assert edit_actions[0].action_type == EditActionType.ADD_CONTENT

    def test_merge_edit_analysis_with_json(self):
        """JSON付き編集解析統合テスト"""
        pattern_actions = []
        pattern_explanation = "パターン解析"
        ai_response = '解析結果 {"edit_actions": [{"action_type": "add_content", "description": "AI提案"}]}'
        
        actions, explanation = self.openai_service._merge_edit_analysis(
            pattern_actions, pattern_explanation, ai_response
        )
        
        assert "パターン解析" in explanation
        assert "解析結果" in explanation
        assert isinstance(actions, list)

    def test_merge_edit_analysis_without_json(self):
        """JSON無し編集解析統合テスト"""
        pattern_actions = []
        pattern_explanation = "パターン解析"
        ai_response = "単純なAI回答"
        
        actions, explanation = self.openai_service._merge_edit_analysis(
            pattern_actions, pattern_explanation, ai_response
        )
        
        assert "パターン解析" in explanation
        assert "単純なAI回答" in explanation
        assert isinstance(actions, list)

    def test_global_openai_service_instance(self):
        """グローバルOpenAIサービスインスタンステスト"""
        assert openai_service is not None
        assert isinstance(openai_service, OpenAIService)

    @pytest.mark.asyncio
    async def test_make_openai_request_o3_model(self):
        """o3モデルリクエストテスト"""
        self.openai_service.model = "o3-mini"
        messages = [{"role": "user", "content": "テスト"}]
        
        with patch('app.services.openai_service.OPENAI_AVAILABLE', True):
            with patch('openai.AsyncOpenAI') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create = AsyncMock()
                
                await self.openai_service._make_openai_request(messages)
                
                # o3モデルでは基本パラメーターのみで呼ばれることを確認
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                assert call_args[1]['model'] == "o3-mini"
                assert call_args[1]['messages'] == messages
                # max_tokens, temperature等が含まれていないことを確認
                assert 'max_tokens' not in call_args[1]
                assert 'temperature' not in call_args[1]

    @pytest.mark.asyncio 
    async def test_make_openai_request_regular_model(self):
        """通常モデルリクエストテスト"""
        self.openai_service.model = "gpt-4"
        messages = [{"role": "user", "content": "テスト"}]
        
        with patch('app.services.openai_service.OPENAI_AVAILABLE', True):
            with patch('openai.AsyncOpenAI') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create = AsyncMock()
                
                await self.openai_service._make_openai_request(messages)
                
                # 通常モデルでは全パラメーターで呼ばれることを確認
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                assert call_args[1]['model'] == "gpt-4"
                assert call_args[1]['messages'] == messages
                assert 'max_tokens' in call_args[1]
                assert 'temperature' in call_args[1]

    @pytest.mark.asyncio
    async def test_call_openai_api_timeout(self):
        """OpenAI APIタイムアウトテスト"""
        self.openai_service.use_mock = False
        
        with patch.object(self.openai_service, '_make_openai_request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()
            
            response_text, citations = await self.openai_service._call_openai_api(
                "システムプロンプト", "ユーザープロンプト"
            )
            
            assert "タイムアウトしました" in response_text
            assert citations == []

    @pytest.mark.asyncio
    async def test_call_openai_api_success(self):
        """OpenAI API成功テスト"""
        self.openai_service.use_mock = False
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "AI回答"
        mock_response.usage.total_tokens = 150
        
        with patch.object(self.openai_service, '_make_openai_request') as mock_request:
            mock_request.return_value = mock_response
            
            with patch.object(self.openai_service, '_generate_smart_citations') as mock_citations:
                mock_citations.return_value = []
                
                response_text, citations = await self.openai_service._call_openai_api(
                    "システムプロンプト", "ユーザープロンプト"
                )
                
                assert response_text == "AI回答"
                assert isinstance(citations, list)