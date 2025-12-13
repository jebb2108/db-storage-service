import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional, Any

import asyncpg

from src.config import config
from src.exc import PaymentException, PostgresConnectionError
from src.logconf import opt_logger as log
from src.models import User, Target, Profile

logger = log.setup_logger("database")


# = КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
class DatabaseService:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool | None] = None
        self.user_locks = defaultdict(asyncio.Lock)
        self.stats_lock = asyncio.Lock()
        self.initialized: bool = False

    async def connect(self):
        """Инициализация пула соединений и создание таблиц"""
        try:
            # Создаем пул соединений
            self._pool = await asyncpg.create_pool(
                config.database.url,
                min_size=config.database.min_size,
                max_size=config.database.max_size,
                timeout=config.database.timeout
            )

            # Создаем таблицы
            await self.__create_users()
            await self.__create_profiles()
            await self.__create_locations()
            await self.__create_words()
            await self.__create_contexts()
            await self.__create_audios()
            # await self.__create_weekly_reports()
            # await self.__create_report_sentences()
            # await self.__creaate_report_translations()
            # await self.__create_report_synonyms()

            self.initialized = True

            logger.debug("Database pool initialized successfully")
            return self

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def __create_users(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                camefrom VARCHAR(50) NOT NULL,
                language VARCHAR(20) NOT NULL,
                fluency SMALLINT NOT NULL,
                topics TEXT[] NOT NULL,
                lang_code TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                blocked_bot BOOLEAN DEFAULT FALSE,
                last_notified TIMESTAMP DEFAULT NOW()
                ); 
                """
            )

    async def __create_words(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                word VARCHAR(100) NOT NULL,
                part_of_speech VARCHAR(50) NOT NULL,
                translation TEXT NOT NULL,
                is_public BOOLEAN DEFAULT FALSE,
                word_state VARCHAR(20) DEFAULT 'NEW',
                emotion VARCHAR(20) DEFAULT 'NEUTRAL',
                correct_spelling BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_id, word)
                ); 
            """
            )

    async def __create_contexts(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contexts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                context TEXT NOT NULL,
                edited BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_id, word_id, context)
                );
            """
            )

    async def __create_audios(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audios (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                audio_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                audio_url TEXT NOT NULL,
                edited BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_id, audio_id, audio_url)
                );
            """
            )

    async def __create_profiles(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                nickname VARCHAR(50) NOT NULL,
                email VARCHAR(50) NOT NULL,
                birthday DATE NOT NULL,
                dating BOOLEAN DEFAULT FALSE,
                gender VARCHAR(50) NULL,
                intro TEXT NULL,
                status VARCHAR(50) NOT NULL,
                UNIQUE (user_id)
                ); 
                """
            )

    async def __create_locations(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS locations (
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                latitude TEXT NULL,
                longitude TEXT NULL,
                city TEXT NULL,
                country TEXT NULL,
                timezone TEXT NULL
                ); 
                """
            )

    # async def __create_weekly_reports(self):
    #     async with self.acquire_connection() as conn:
    #         await conn.execute(
    #             """
    #             CREATE TABLE IF NOT EXISTS weekly_reports (
    #             report_id SERIAL PRIMARY KEY,
    #             user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    #             status TEXT DEFAULT 'OK',
    #             generation_date TIMESTAMP DEFAULT NOW(),
    #             sent BOOLEAN DEFAULT FALSE
    #             );
    #             """
    #         )
    #
    # async def __create_report_sentences(self):
    #     async with self.acquire_connection() as conn:
    #         await conn.execute(
    #             """
    #             CREATE TABLE IF NOT EXISTS report_sentences (
    #             word_id SERIAL PRIMARY KEY,
    #             report_id INT REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
    #             word VARCHAR(100) NOT NULL,
    #             sentence TEXT NOT NULL,
    #             audio_url TEXT NOT NULL,
    #             options TEXT[] NOT NULL,
    #             correct_index INT NOT NULL
    #             );
    #             """
    #         )
    #
    # async def __creaate_report_translations(self):
    #     async with self.acquire_connection() as  conn:
    #         await conn.execute(
    #             """
    #             CREATE TABLE IF NOT EXISTS report_translations (
    #             word_id SERIAL PRIMARY KEY,
    #             report_id INT REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
    #             word VARCHAR(100) NOT NULL,
    #             audio_url TEXT NOT NULL,
    #             options TEXT[] NOT NULL,
    #             correct_index INT NOT NULL
    #             );
    #             """
    #         )
    #
    # async def __create_report_synonyms(self):
    #     async with self.acquire_connection() as conn:
    #         await conn.execute("""
    #         CREATE TABLE IF NOT EXISTS report_synonyms (
    #         word_id SERIAL PRIMARY KEY,
    #         report_id INT REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
    #         word VARCHAR(100) NOT NULL,
    #         options TEXT[] NOT NULL,
    #         correct_index INT NOT NULL
    #         );
    #         """
    #     )


    @asynccontextmanager
    async def acquire_connection(self):
        """Асинхронный контекстный менеджер для работы с соединениями"""
        conn = await self._pool.acquire()
        try:
            yield conn
        finally:
            await self._pool.release(conn)

    async def get_version(self):
        """ Получает версию БД от Postgres """
        async with self.acquire_connection() as conn:
            try:
                return await conn.fetchval(
                    """
                    SELECT VERSION();
                    """
                )
            except Exception as e:
                logger.error(f"Error connecting to DB: {e}")
                raise PostgresConnectionError


    async def save_user(self, user_data: User) -> None:
        """ Сохраняет нового пользователя """
        async with self.acquire_connection() as conn:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, camefrom, language, fluency, topics, lang_code) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET username = EXCLUDED.username,
                        camefrom = EXCLUDED.camefrom,
                        first_name = EXCLUDED.first_name,
                        language = EXCLUDED.language,
                        fluency = EXCLUDED.fluency,
                        topics = EXCLUDED.topics,
                        lang_code = EXCLUDED.lang_code
                """,
                    user_data.user_id,
                    user_data.username,
                    user_data.first_name,
                    user_data.camefrom,
                    user_data.language,
                    user_data.fluency,
                    user_data.topics,
                    user_data.lang_code,
                )
                logger.info(f"User {user_data.user_id} created/updated: {result}")


            except Exception as e:
                logger.error(f"Error creating/updating user {user_data.user_id}: {e}")
                raise

    async def save_profile(self, profile_data: Profile) -> None:
        """ Сохраняет профиль пользователя """
        async with self.acquire_connection() as conn:
            try:
                await conn.execute(
                    """
                INSERT INTO profiles 
                (
                    user_id, nickname, 
                    email, birthday, 
                    dating, gender, 
                    intro, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id) DO UPDATE
                SET status = EXCLUDED.status,
                    nickname = EXCLUDED.nickname,
                    email = EXCLUDED.email,
                    birthday = EXCLUDED.birthday,
                    dating = EXCLUDED.dating,
                    gender = EXCLUDED.gender,
                    intro = EXCLUDED.intro
                """,
                    profile_data.user_id, profile_data.nickname, profile_data.email, profile_data.birthday,
                    profile_data.dating, profile_data.gender, profile_data.intro, profile_data.status
                )
                logger.debug(
                    f"User {profile_data.user_id} profile added. Their name: {profile_data.nickname}, "
                    f"email: {profile_data.email}, birthday: {profile_data.birthday}, dating: {profile_data.dating}, "
                    f"gender: {profile_data.gender}, status: {profile_data.status},\n intro: {profile_data.intro}"
                )

            except Exception as e:
                logger.error(f"Error creating/updating user profile {profile_data.user_id}: {e}")
                raise


    async def get_all_users_for_notification(self) -> List[Tuple[int, str]]:
        async with self.acquire_connection() as conn:
            reports = await conn.fetch(
                "SELECT DISTINCT user_id, last_notified FROM users WHERE user_id IS NOT NULL AND blocked_bot = false"
            )
            return [ ( int(report["user_id"]), report["last_notified"] ) for report in reports ]

    async def save_location(
            self,
            user_id: int,
            latitude: Optional[str] = None,
            longitude: Optional[str] = None,
            city: Optional[str] = None,
            country: Optional[str] = None,
            tzone: Optional[str] = None,
    ) -> None:
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                INSERT INTO locations (user_id, latitude, longitude, city, country, timezone)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (user_id) DO UPDATE
                SET latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    city = EXCLUDED.city,
                    country = EXCLUDED.country,
                    timezone = EXCLUDED.timezone
                """,
                user_id,
                latitude,
                longitude,
                city,
                country,
                tzone,
            )
            logger.info(
                f"User {user_id} location added: {latitude}, {longitude}, {city}, {country}, {tzone}"
            )
            return

    async def query_criteria_by_target(self, user_id: int, target: Target) -> dict:
        async with self.acquire_connection() as conn:
            try:
                if target is Target.ALL:
                    # Возвращает все данные о пользователе
                    row = await conn.fetchrow(
                        """
                        SELECT 
                            u.*,
                            p.nickname, p.email, p.birthday, 
                            p.dating, p.gender, p.intro, p.status
                        FROM users u
                        LEFT JOIN profiles p 
                          ON u.user_id = p.user_id
                        WHERE u.user_id = $1
                        """,
                        user_id,
                    )
                elif target.value in ['users', 'profiles']:
                    row = await conn.fetchrow(
                        f"SELECT * FROM {target.value} WHERE user_id = $1", user_id
                    )

                else:
                    # Обновляет нужный критерий пользователя,
                    # динамическая выбирая талицу в БД
                    table = {
                        'language': 'users', 'fluency': 'users',
                        'topics': 'users', 'username': 'users',
                        'nickname': 'profiles', 'email': 'profiles',
                        'birthday': 'profiles', 'dating': 'profiles',
                        'gender': 'profiles', 'about': 'profiles'
                    }.get(target.value, None)

                    if table:
                        # Отправляет SQL запрос в БД
                        row = await conn.fetchrow(
                            f"SELECT {target.value} FROM {table} WHERE user_id = $1", user_id
                        )

                return dict(row) if row else None

            except Exception as e:
                logger.error(f"Error getting target criterion: {e}")

    async def update_profile(self, user_id: int, target: Target, data: str) -> None:
        """ Обновляет одну из выбранных таблиц с выбранными аргументами """
        async with self.acquire_connection() as conn:
            table = {
                'language': 'users', 'fluency': 'users',
                'topics': 'users', 'username': 'users',
                'nickname': 'profiles', 'email': 'profiles',
                'birtday': 'profiles','dating': 'profiles',
                'gender': 'profiles', 'about': 'profiles'
            }.get(target.value, None)

            if table is None: return
            try:
                await conn.execute(
                    f"UPDATE {table} SET {target.value} = $1 WHERE user_id = $2",
                    data, user_id,
                )
            except Exception as e:
                raise logger.error(f'Error updating profile: {e}')

    async def get_location(self, user_id: int):
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow(
                "SELECT city, country FROM locations WHERE user_id = $1", user_id
            )
            return dict(row) if row else None


    async def get_words_by_different_users(self, word: str) -> Dict[str, Dict[str, Any]]:
        async with self.acquire_connection() as conn:
            rows = await conn.fetch("""
                SELECT p.nickname, w.user_id, w.word, w.part_of_speech, w.translation, w.created_at
                FROM words w
                LEFT JOIN profiles p ON w.user_id = p.user_id
                WHERE w.word = $1 AND w.is_public = true AND p.nickname IS NOT NULL
            """, word)

            word_dict = {}
            for row in rows:
                user_id = str(row["user_id"])
                word_dict[user_id] = {
                    "word": row["word"],
                    "part_of_speech": row["part_of_speech"],
                    "translation": row["translation"],
                    "nickname": row["nickname"],
                    "created_at": row["created_at"].isoformat()
                }
            return word_dict


    async def get_words(self, user_id: int):
        async with self.acquire_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                w.id
                ,w.word
                ,w.part_of_speech
                ,w.translation 
                ,w.is_public
                ,c.context
                FROM words w
                LEFT JOIN contexts c
                    ON w.id = c.word_id
                WHERE w.user_id = $1 
                ORDER BY w.word""",
                user_id,
            )
            return [
                (row["id"], row["word"], row["part_of_speech"], row["translation"], row["is_public"], row["context"])
                for row in rows
            ]

    async def add_word(self, user_id: int, word: str, pos: str, value: str, is_public: bool, context: str = None,
                       audio=None):
        async with self.acquire_connection() as conn:

            is_active = await conn.fetchval(
                "SELECT is_active FROM users WHERE user_id = $1", user_id
            )
            if not is_active: raise PaymentException
            try:
                row = await conn.fetchrow(
                    """INSERT INTO words (user_id, word, part_of_speech, translation, is_public) 
                    VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    user_id,
                    word,
                    pos,
                    value,
                    is_public
                )

                if context:
                    await conn.execute(
                        """INSERT INTO contexts (user_id, word_id, context) 
                        VALUES ($1, $2, $3)""",
                        user_id, row["id"], context
                    )

                if audio:
                    await conn.execute(
                        """INSERT INTO audios (user_id, audio_id, audio_url) 
                        VALUES ($1, $2, $3)""",
                        user_id, row["id"], audio
                    )


            except Exception as e:
                raise logger.error(f"Database error: {e}")


    async def search_word(self, user_id: int, word: str) -> Optional[Dict[str, Any]]:
        async with self.acquire_connection() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    SELECT user_id, word, part_of_speech, translation, created_at
                    FROM words WHERE user_id = $1 AND word = $2
                    """, user_id, word
                )
                if row:
                    return {
                        "user_id": row["user_id"],
                        "word": row["word"],
                        "part_of_speech": row["part_of_speech"],
                        "translation": row["translation"],
                        "created_at": row["created_at"].isoformat()
                    }
                return None

            except Exception as e:
                logger.error(f"Database error in search_word: {e}")
                return None


    async def delete_word(self, user_id: int, word_id: int) -> bool:
        async with self.acquire_connection() as conn:
            result = await conn.execute(
                "DELETE FROM words WHERE user_id = $1 AND id = $2", user_id, word_id
            )
            return "DELETE" in result

    async def update_word(
            self, user_id: int, old_word: str, new_word: str, pos: str, value: str
    ) -> bool:
        async with self.user_locks[user_id]:
            async with self.acquire_connection() as conn:
                async with conn.transaction():
                    if old_word != new_word:
                        await conn.execute(
                            "DELETE FROM words WHERE user_id = $1 AND word = $2",
                            user_id,
                            old_word,
                        )
                        await conn.execute(
                            "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                            user_id,
                            new_word,
                            pos,
                            value,
                        )
                        return True
                    else:
                        result = await conn.execute(
                            """UPDATE words 
                            SET part_of_speech = $1, translation = $2 
                            WHERE user_id = $3 AND word = $4""",
                            pos,
                            value,
                            user_id,
                            new_word,
                        )
                        return "UPDATE" in result

    async def mark_repeated_words(self, nickname: str, message: str) -> bool:
        """Помечает слова из сообщения как повторенные одним запросом"""
        async with self.acquire_connection() as conn:
            # Нормализуем слова из сообщения
            message_words = {word.strip().lower() for word in message.split()}

            # Обновляем состояние слов одним запросом
            result = await conn.execute(
                """
                UPDATE words 
                SET word_state = 'REPEATED'
                WHERE user_id = (
                    SELECT p.user_id
                    FROM profiles p
                    WHERE p.nickname = $1
                    LIMIT 1
                )
                AND word_state = 'NEW'
                AND LOWER(word) = ANY($2)
                """,
                nickname,
                list(message_words)
            )

            # Проверяем, были ли обновлены какие-либо строки
            return bool(result)

    async def update_notified_time(self, user_id: int) -> None:
        curr_time = datetime.now(tz=config.tz_info).replace(tzinfo=None)
        async with self.acquire_connection() as conn:
            await conn.execute(
                "UPDATE users SET last_notified = $1 WHERE user_id = $2", curr_time, user_id
            )

    # Temperorary solution
    async def get_user_stats(self, user_id: int):
        async with self.stats_lock:
            async with self.acquire_connection() as conn:
                try:
                    all_words_count_row = await conn.fetchrow(
                        """
                        SELECT
                          COUNT(*) FILTER (WHERE part_of_speech = 'noun') AS nouns,
                          COUNT(*) FILTER (WHERE part_of_speech = 'verb') AS verbs,
                          COUNT(*) FILTER (WHERE part_of_speech = 'adjective') AS adjectives,
                          COUNT(*) FILTER (WHERE part_of_speech = 'adverb') AS adverbs,
                          COUNT(*) FILTER (WHERE part_of_speech = 'other') AS other
                        FROM words
                        WHERE user_id = $1
                        """,
                        user_id,
                    )

                    if not all_words_count_row:
                        return 0, 0, 0

                    # Преобразуем None в 0 и суммируем
                    nouns = all_words_count_row.get('nouns', 0) or 0
                    verbs = all_words_count_row.get('verbs', 0) or 0
                    adjectives = all_words_count_row.get('adjectives', 0) or 0
                    adverbs = all_words_count_row.get('adverbs', 0) or 0
                    other = all_words_count_row.get('other', 0) or 0

                    total = nouns + verbs + adjectives + adverbs + other

                    return total, nouns, verbs

                except Exception as e:
                    logger.error(f"Database error in get_user_stats: {e}")
                    return 0, 0, 0

    async def get_user_stats_last_week(self, user_id: int):
        async with self.stats_lock:
            async with self.acquire_connection() as conn:
                try:
                    all_words_last_week_count_row = await conn.fetchrow(
                        """SELECT COUNT(*) FROM words WHERE user_id = $1 AND created_at >= $2""",
                        user_id,
                        datetime.now() - timedelta(days=7),
                    )
                    if all_words_last_week_count_row:
                        return all_words_last_week_count_row["count"]

                    else:
                        return 0

                except Exception as e:
                    logger.error(f"Database error: {e}")
                    return None

    async def user_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", user_id)
            )

    async def profile_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow(
                    "SELECT 1 FROM profiles WHERE user_id = $1", user_id
                )
            )

    async def location_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow(
                    "SELECT 1 FROM locations WHERE user_id = $1", user_id
                )
            )

    async def nickname_exists(self, nickname: str):
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow(
                    "SELECT 1 FROM profiles WHERE nickname = $1", nickname
                )
            )

    async def get_words_by_user(self) -> List[Dict]:
        current_time = datetime.now(tz=config.tz_info).replace(tzinfo=None)
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                """
                SELECT user_id, ARRAY_AGG(DISTINCT word) as words
                FROM words 
                WHERE word_state != 'LEARNED' 
                   AND word IS NOT NULL 
                   AND $1 - created_at >= CASE word_state
                       WHEN 'NEW' THEN INTERVAL '1 days'
                       WHEN 'REPEATED' THEN INTERVAL '5 days'
                       WHEN 'REINFORCED' THEN INTERVAL '14 days'
                   END 
                GROUP BY user_id
                """, current_time
            )

    async def create_report(self, user_id: int) -> int:
        async with self.acquire_connection() as conn:
            return await conn.fetchval(
                "INSERT INTO weekly_reports (user_id) VALUES ($1) RETURNING report_id",
                user_id,
            )

    async def add_words_to_report(self, report_id: int, report_type: str, words: List[Dict]):
        async with self.acquire_connection() as conn:
            if report_type == config.SENTENCE:
                for item in words:
                    await conn.execute(
                        "INSERT INTO report_sentences (report_id, word, sentence, audio_url, options, correct_index) "
                        "VALUES ($1, $2, $3, $4, $5, $6)",
                        report_id,
                        item["word"],
                        item["sentence"],
                        item["audio_url"],
                        item["options"],
                        item["correct_index"],
                    )
            elif report_type == config.TRANSLATION:
                for item in words:
                    await conn.execute(
                        "INSERT INTO report_translations (report_id, word, audio_url, options, correct_index) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        report_id,
                        item["word"],
                        item["audio_url"],
                        item["options"],
                        item["correct_index"],
                    )
            elif report_type == config.SYNONYM:
                for item in words:
                    await conn.execute(
                        "INSERT INTO report_synonyms (report_id, word, options, correct_index) "
                        "VALUES ($1, $2, $3, $4)",
                        report_id,
                        item["word"],
                        item["options"],
                        item["correct_index"],
                    )

    async def get_report(self, report_id):
        async with self.acquire_connection() as conn:
            return await conn.fetchrow(
                "SELECT * FROM weekly_reports WHERE report_id = $1", report_id
            )

    async def get_word_data(self, word_id):
        async with self.acquire_connection() as conn:
            return await conn.fetchrow(
                "SELECT * FROM report_words WHERE word_id = $1", word_id
            )

    async def get_weekly_words(self, report_id):
        async with self.acquire_connection() as conn:
            result = await conn.fetch(
                "SELECT * FROM report_words WHERE report_id = $1", report_id
            )
            return [dict(row) for row in result]

    async def get_words_ids(self, report_id):
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                "SELECT word_id FROM report_words WHERE report_id = $1", report_id
            )

    async def get_pending_reports(self) -> List[Dict]:
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                "SELECT report_id, user_id FROM weekly_reports WHERE sent = FALSE AND status = 'OK'"
            )

    async def update_word_state(self, user_id: int, word: str, correct: bool):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                UPDATE words 
                SET word_state = CASE 
                    WHEN $3 = true THEN 
                        CASE word_state 
                            WHEN 'NEW' THEN 'REPEATED'
                            WHEN 'REPEATED' THEN 'REINFORCED' 
                            WHEN 'REINFORCED' THEN 'LEARNED'
                            ELSE word_state
                        END
                    ELSE 
                        CASE word_state 
                            WHEN 'REPEATED' THEN 'NEW'
                            WHEN 'REINFORCED' THEN 'REPEATED'
                            WHEN 'LEARNED' THEN 'REINFORCED'
                            ELSE word_state
                        END
                END
                WHERE user_id = $1 AND word = $2
            """, user_id, word, correct
            )

    async def mark_user_as_blocked(self, user_id: int):
        async with self.acquire_connection() as conn:
            await conn.execute(
                "UPDATE users SET is_active = FALSE, blocked_bot = TRUE WHERE user_id = $1",
                user_id,
            )
            logger.info(f"Пользователь {user_id} помечен как заблокированный в БД.")

    # Обновить mark_report_as_sent для приема статуса
    async def mark_report_as_sent(self, report_id: int, status: str = "OK"):
        async with self.acquire_connection() as conn:
            await conn.execute(
                "UPDATE weekly_reports SET generation_date = NOW(), sent = TRUE, status = $1 WHERE report_id = $2",
                status,
                report_id,
            )
            logger.info(f"Отчет {report_id} помечен как {status} в БД.")

    async def is_user_blocked(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return await conn.fetchval(
                "SELECT blocked_bot FROM users WHERE user_id = $1", user_id
            )

    async def cleanup_old_reports(self, days: int) -> Tuple[int, int]:
        cutoff_date = datetime.now() - timedelta(days=days)
        async with self.acquire_connection() as conn:
            words_rows = await conn.fetch(
                "DELETE FROM report_words "
                "WHERE report_id IN ("
                "   SELECT report_id FROM weekly_reports "
                "   WHERE generation_date < $1"
                ") RETURNING word_id",
                cutoff_date,
            )
            reports_rows = await conn.fetch(
                "DELETE FROM weekly_reports WHERE generation_date < $1 RETURNING report_id",
                cutoff_date,
            )
            return len(reports_rows), len(words_rows)

    async def create_match_id(self, match_id: str) -> None:
        async with self.acquire_connection() as conn:
            await conn.execute("""
            INSERT INTO match_ids (match_id) VALUES ($1)
            """, match_id
                               )

    def clean_locks(self):
        """Периодически очищаем неиспользуемые блокировки"""
        user_ids = list(self.user_locks.keys())
        for user_id in user_ids:
            if user_id in self.user_locks and not self.user_locks[user_id].locked():
                del self.user_locks[user_id]

    async def disconnect(self):
        if self.initialized:
            await self._pool.close()


database_service = DatabaseService()
