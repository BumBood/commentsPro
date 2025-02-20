import logging
import pandas as pd
from telethon.tl.types import User
from typing import List, Dict
from .session_manager import SessionManager
import asyncio


class CommentParser:
    def __init__(self, sessions_dir: str = "sessions"):
        self.session_manager = SessionManager(sessions_dir)
        self.logger = logging.getLogger(__name__)

    async def parse_comments(self, post_link: str, limit: int = None) -> pd.DataFrame:
        """
        Парсит комментарии из поста Telegram и сохраняет их в DataFrame

        Args:
            post_link: ссылка на пост
            limit: максимальное количество комментариев для парсинга
        """
        self.logger.info(f"Начало парсинга комментариев для поста: {post_link}")
        client = await self.session_manager.get_available_session()
        if not client:
            self.logger.error("Нет доступных сессий")
            raise Exception("Нет доступных сессий")

        try:
            # Извлекаем channel_id и message_id из ссылки
            # Пример ссылки: https://t.me/channel_name/1234
            channel_name = post_link.split("/")[-2]
            message_id = int(post_link.split("/")[-1])
            self.logger.debug(
                f"Извлечены данные: канал={channel_name}, id сообщения={message_id}"
            )

            comments_data: List[Dict] = []
            count = 0

            # Получаем канал
            channel = await client.get_entity(channel_name)
            # Получаем сообщение
            message = await client.get_messages(channel, ids=message_id)
            # Получаем комментарии
            users_data = {}  # Словарь для хранения информации о пользователях

            async for comment in client.iter_messages(channel, reply_to=message.id):
                if limit and count >= limit:
                    break

                if type(comment.sender) is User:
                    comment_data = {
                        "comment_id": comment.id,
                        "user_id": comment.sender_id if comment.sender else None,
                        "username": comment.sender.username if comment.sender else None,
                        "full_name": (
                            f"{comment.sender.first_name} {comment.sender.last_name or ''}"
                            if comment.sender
                            else None
                        ),
                        "text": comment.text or comment.raw_text or "",
                        "date": comment.date.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    comments_data.append(comment_data)
                    count += 1

                    # Собираем информацию о пользователях
                    if comment.sender and comment.sender_id not in users_data:
                        sender = comment.sender
                        # Обработка статуса
                        status = sender.status
                        if hasattr(status, "was_online"):
                            formatted_status = status.was_online.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        elif hasattr(status, "expires"):
                            formatted_status = "В сети"
                        else:
                            formatted_status = "Недавно"

                        users_data[comment.sender_id] = {
                            "ID отправителя": sender.id,
                            "Тип": "user",
                            "Никнейм": sender.username,
                            "Имя | Название канала": f"{sender.first_name} {sender.last_name or ''}",
                            "Телефон": getattr(sender, "phone", None),
                            "Последняя активность": formatted_status,
                        }
                    self.logger.debug(f"Обработан комментарий id={comment.id}")

            df_comments = pd.DataFrame(comments_data)
            df_users = pd.DataFrame(list(users_data.values()))

            # Создаем словарь с двумя DataFrame для разных листов
            df = {"Комментарии": df_comments, "Пользователи": df_users}
            self.logger.info(
                f"Парсинг завершен. Получено {len(comments_data)} комментариев"
            )

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге комментариев: {str(e)}")
            raise
        finally:
            await self.session_manager.release_session(client=client)
            self.logger.debug("Сессия освобождена")
            return df

    def save_to_excel(
        self, df_dict: Dict[str, pd.DataFrame], output_file: str = "result.xlsx"
    ):
        """Сохраняет DataFrames в Excel файл на разные листы"""
        self.logger.info(f"Сохранение данных в файл: {output_file}")
        try:
            # Создаем Excel writer
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # Сохраняем каждый DataFrame на отдельный лист
                for sheet_name, df in df_dict.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                    # Получаем объект листа
                    worksheet = writer.sheets[sheet_name]

                    # Подгоняем ширину каждой колонки под максимальную длину содержимого
                    for idx, col in enumerate(df.columns):
                        # Получаем максимальную длину в колонке
                        max_length = max(
                            df[col].astype(str).apply(len).max(), len(str(col))
                        )
                        # Устанавливаем ширину колонки
                        worksheet.column_dimensions[chr(65 + idx)].width = (
                            max_length + 2
                        )

            self.logger.info("Данные успешно сохранены")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении в Excel: {str(e)}")
            raise

    async def get_comments_count(self, post_link: str) -> int:
        """Получает количество комментариев в посте"""
        client = await self.session_manager.get_available_session()
        if not client:
            raise Exception("Нет доступных сессий")

        try:
            channel_name = post_link.split("/")[-2]
            message_id = int(post_link.split("/")[-1])

            channel = await client.get_entity(channel_name)
            message = await client.get_messages(channel, ids=message_id)

            # Получаем количество комментариев напрямую из сообщения
            return message.replies.replies if message.replies else 0

        finally:
            await self.session_manager.release_session(client)


# Пример использования:
async def main():
    parser = CommentParser()

    post_link = "https://t.me/proofzzz/30466"
    df = await parser.parse_comments(post_link)
    parser.save_to_excel(df)


if __name__ == "__main__":
    asyncio.run(main())
