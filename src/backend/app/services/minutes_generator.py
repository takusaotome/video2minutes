import re

import openai

from app.config import settings
from app.utils.logger import LoggerMixin


class MinutesGeneratorService(LoggerMixin):
    """議事録生成サービス"""

    def __init__(self):
        """OpenAI クライアントを初期化"""
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.logger.info("MinutesGeneratorService初期化完了")

    async def generate_minutes(
        self,
        transcript: str,
        meeting_name: str = "会議",
        date: str = "",
        attendees: str = "参加者",
    ) -> str:
        """文字起こしから議事録を生成"""

        transcript_length = len(transcript)
        self.logger.info(
            f"議事録生成開始: {meeting_name} (文字起こし: {transcript_length}文字)"
        )

        # 現在のプロンプトテンプレートを使用（既存コードから）
        prompt = self._build_prompt(transcript, meeting_name, date, attendees)

        try:
            self.logger.info(f"GPT API呼び出し開始 - モデル: {settings.gpt_model}")

            # GPT-4.1モデルでフォールバック機能付き
            minutes_text = await self._call_chat_completion(prompt, settings.gpt_model)

            # マークダウンのコードフェンスを除去
            minutes_text = self._strip_code_fence(minutes_text)

            result_length = len(minutes_text)
            self.logger.info(
                f"議事録生成完了: {meeting_name} (出力: {result_length}文字)"
            )

            return minutes_text

        except Exception as e:
            self.logger.error(
                f"議事録生成エラー: {meeting_name} - {str(e)}", exc_info=True
            )
            raise RuntimeError(f"議事録生成中にエラーが発生しました: {str(e)}")

    def _build_prompt(
        self, transcript: str, meeting_name: str, date: str, attendees: str
    ) -> str:
        """プロンプトを構築"""

        return f"""##### ① ロール定義（変更不要）
あなたは「戦略系コンサルの議事録ライター」です。
- 文字起こし全文から要点を抽出し、読み手が 3 分で全体像と次のアクションを把握できる議事録を作成してください。
- 未決事項や検討タスクがあれば「アクションアイテム」として必ず表にまとめ、担当者と期限を推論・記載します。
- 決定事項・議論の経緯・論点・参考情報は「議事内容の詳細」に整理します。
- 出力は **Markdown** 形式で。

##### ② 出力仕様（変更不要）
**出力フォーマット**
### 会議情報
   - **会議名**: {meeting_name}
   - **開催日時**: {date}
   - **出席者**: {attendees}

### 2. アクションアイテム
   | No. | アクションアイテム | 担当 | 重要度 | 期限 | 備考 |
   |-----|------------------|------|------|------|------|
   | {{自動生成}} |

   **重要度凡例**
   🔴: 高   🟡: 中   🟢: 低

### 3. 議事内容の詳細
   - #### 決定事項
     - {{箇条書き}}
   - #### 主要議題と論点
     1. **{{議題1}}**
        - 背景: …
        - 主な発言要旨: …
     2. **{{議題2}}**
        - …
   - #### 次回以降へのメモ / その他
     - …

##### ③ 入力欄（ここだけ毎回差し替え）
以下にミーティングの文字起こし全文を <<Transcript>> タグで囲んで貼り付けてください。

<<Transcript>>
{transcript}
<<Transcript>>"""

    async def _call_chat_completion(self, prompt: str, prefer_model: str) -> str:
        """OpenAI Chat APIを呼び出し（フォールバック機能付き）"""
        for model in (prefer_model, "gpt-4.1", "gpt-4.1-mini"):
            try:
                self.logger.debug(f"APIリクエスト: モデル={model}")

                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )

                self.logger.info(f"API呼び出し成功: モデル={model}")
                return response.choices[0].message.content

            except openai.NotFoundError:
                self.logger.warning(
                    f"モデルが見つかりません: {model} - 次のモデルを試行"
                )
                continue
            except Exception as e:
                self.logger.error(
                    f"OpenAI API呼び出しエラー: モデル={model} - {str(e)}"
                )
                raise RuntimeError(f"OpenAI API呼び出しエラー: {str(e)}")

        self.logger.error("すべてのモデルで失敗しました")
        raise RuntimeError("利用可能なモデルが見つかりません")

    def _strip_code_fence(self, text: str) -> str:
        """マークダウンのコードフェンスを除去"""
        text = text.strip()

        # ```markdown または ``` で始まって ``` で終わる場合
        if text.startswith("```"):
            text = re.sub(r"^```(?:[a-zA-Z0-9_+-]*)?\n", "", text)
            text = re.sub(r"\n```\s*$", "", text)

        return text.lstrip("\n")

    async def generate_summary(self, minutes: str) -> str:
        """議事録からサマリーを生成"""

        prompt = f"""以下の議事録から、要点を3行以内でまとめてください。

議事録:
{minutes}

要点サマリー（3行以内）:"""

        try:
            summary_text = await self._call_chat_completion(prompt, settings.gpt_model)
            return summary_text.strip()

        except Exception as e:
            raise RuntimeError(f"サマリー生成中にエラーが発生しました: {str(e)}")
