from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.minutes_generator import MinutesGeneratorService


class TestMinutesGeneratorService:
    """MinutesGeneratorServiceのテスト"""

    @pytest.fixture
    def minutes_service(self):
        """MinutesGeneratorServiceインスタンス"""
        return MinutesGeneratorService()

    @pytest.fixture
    def mock_openai_client(self):
        """OpenAIクライアントのモック"""
        mock_client = Mock()
        mock_client.chat = Mock()
        mock_client.chat.completions = Mock()
        mock_client.chat.completions.create = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_generate_minutes_success(
        self, minutes_service, mock_openai_client, mock_settings
    ):
        """議事録生成成功テスト"""
        transcription = (
            "これはテスト用の文字起こし結果です。会議の内容について話し合いました。"
        )
        expected_minutes = "## 会議議事録\n\n### 要約\nテスト会議の内容です。"

        # ChatCompletionレスポンスのモック
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = expected_minutes

        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch.object(minutes_service, "client", mock_openai_client):
            result = await minutes_service.generate_minutes(transcription)

            # 結果確認
            assert result == expected_minutes

            # OpenAI API呼び出し確認
            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args[1]
            assert call_args["model"] == mock_settings.gpt_model
            assert call_args["temperature"] == 0.2
            assert len(call_args["messages"]) == 1  # user message only

    @pytest.mark.asyncio
    async def test_generate_minutes_empty_transcription(
        self, minutes_service, mock_openai_client
    ):
        """空の文字起こしでの議事録生成テスト"""
        # 空の文字起こしでも正常に処理される（実装に合わせて）
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "議事録なし"

        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch.object(minutes_service, "client", mock_openai_client):
            result = await minutes_service.generate_minutes("")

            # 結果が返されることを確認
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_minutes_api_error(
        self, minutes_service, mock_openai_client
    ):
        """OpenAI APIエラーのテスト"""
        transcription = "テスト用の文字起こし結果"

        # API呼び出しでエラーを発生させる
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(minutes_service, "client", mock_openai_client):
            with pytest.raises(RuntimeError) as exc_info:
                await minutes_service.generate_minutes(transcription)

            assert "議事録生成中にエラーが発生しました" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_minutes_empty_response(
        self, minutes_service, mock_openai_client
    ):
        """空のレスポンスのテスト"""
        transcription = "テスト用の文字起こし結果"

        # 空のレスポンスを返すようにモック
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = ""

        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch.object(minutes_service, "client", mock_openai_client):
            result = await minutes_service.generate_minutes(transcription)

            # 空の結果でも正常に処理される（実装に合わせて）
            assert isinstance(result, str)

    def test_build_prompt(self, minutes_service):
        """プロンプト構築テスト"""
        transcript = "テスト用の文字起こし"
        meeting_name = "テスト会議"
        date = "2024-01-01"
        attendees = "田中, 佐藤"

        result = minutes_service._build_prompt(
            transcript, meeting_name, date, attendees
        )

        # プロンプトに必要な要素が含まれていることを確認
        assert isinstance(result, str)
        assert meeting_name in result
        assert date in result
        assert attendees in result
        assert transcript in result
        assert "Transcript" in result

    def test_strip_code_fence(self, minutes_service):
        """コードフェンス除去テスト"""
        # マークダウンコードフェンス付きテキスト
        text_with_fence = "```markdown\n## 議事録\n\n内容\n```"

        result = minutes_service._strip_code_fence(text_with_fence)

        # コードフェンスが除去されていることを確認
        assert "```" not in result
        assert "## 議事録" in result
        assert "内容" in result

    def test_strip_code_fence_no_fence(self, minutes_service):
        """コードフェンスなしテキストのテスト"""
        text = "## 議事録\n\n内容"

        result = minutes_service._strip_code_fence(text)

        # 元のテキストがそのまま返されることを確認
        assert result == text

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, minutes_service, mock_openai_client):
        """サマリー生成成功テスト"""
        minutes = "## 会議議事録\n\n決定事項: 新プロジェクト開始\n期限: 来月まで"
        expected_summary = "新プロジェクトの開始が決定されました。"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = expected_summary

        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch.object(minutes_service, "client", mock_openai_client):
            result = await minutes_service.generate_summary(minutes)

            # 結果確認
            assert result == expected_summary

            # API呼び出し確認
            mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_error(self, minutes_service, mock_openai_client):
        """サマリー生成エラーテスト"""
        minutes = "テスト議事録"

        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(minutes_service, "client", mock_openai_client):
            with pytest.raises(RuntimeError) as exc_info:
                await minutes_service.generate_summary(minutes)

            assert "サマリー生成中にエラーが発生しました" in str(exc_info.value)


class TestMinutesGeneratorServiceConfiguration:
    """MinutesGeneratorServiceの設定関連テスト"""

    def test_initialization_with_api_key(self, mock_settings):
        """API キーを使用した初期化テスト"""
        with patch("openai.AsyncOpenAI") as mock_openai:
            MinutesGeneratorService()

            # OpenAI クライアントが正しいAPI キーで初期化されることを確認
            mock_openai.assert_called_once_with(api_key=mock_settings.openai_api_key)

    @pytest.mark.asyncio
    async def test_generate_minutes_uses_correct_settings(self, mock_settings):
        """議事録生成で正しい設定が使用されることのテスト"""
        service = MinutesGeneratorService()
        transcription = "テスト用文字起こし"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "テスト議事録"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(service, "client", mock_client):
            await service.generate_minutes(transcription)

            # 正しい設定が使用されることを確認
            call_args = mock_client.chat.completions.create.call_args[1]
            assert call_args["model"] == mock_settings.gpt_model
            assert call_args["temperature"] == 0.2

    def test_build_prompt_content(self):
        """プロンプト内容テスト"""
        service = MinutesGeneratorService()
        # プロンプト構築メソッドが正しく動作することを確認
        prompt = service._build_prompt("テスト", "会議", "2024-01-01", "参加者")

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "議事録" in prompt
        assert "アクションアイテム" in prompt


class TestMinutesGeneratorIntegration:
    """MinutesGeneratorServiceの統合テスト"""

    @pytest.mark.asyncio
    async def test_full_minutes_generation_flow(self):
        """議事録生成の完全なフローテスト"""
        service = MinutesGeneratorService()

        # 実際の文字起こしに近いテストデータ
        transcription = """
        おはようございます。本日は貴重なお時間をいただき、ありがとうございます。
        新プロジェクトについて話し合いたいと思います。
        予算は500万円を予定しており、期間は6ヶ月を想定しています。
        チームメンバーは5名で構成する予定です。
        来週までに詳細な計画書を作成し、承認を得る必要があります。
        何かご質問はございますか。
        """

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[
            0
        ].message.content = """
        ## 会議議事録
        
        ### 概要
        新プロジェクトに関する打ち合わせ
        
        ### 参加者
        - プロジェクトメンバー
        
        ### 決定事項
        - 予算: 500万円
        - 期間: 6ヶ月
        - チーム規模: 5名
        
        ### アクション項目
        - 来週までに詳細計画書を作成
        """

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(service, "client", mock_client):
            result = await service.generate_minutes(transcription)

            # 結果の基本的な構造を確認
            assert "議事録" in result
            assert "500万円" in result
            assert "6ヶ月" in result
            assert "5名" in result

    @pytest.mark.asyncio
    async def test_long_transcription_handling(self):
        """長い文字起こしの処理テスト"""
        service = MinutesGeneratorService()

        # 長いテキストを生成
        long_transcription = "この会議では重要な議論が行われました。" * 1000

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "## 長い会議の議事録\n\n要約内容"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(service, "client", mock_client):
            result = await service.generate_minutes(long_transcription)

            # 長いテキストでも正常に処理されることを確認
            assert isinstance(result, str)
            assert len(result) > 0
            assert "議事録" in result
