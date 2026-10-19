import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env!")

supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())

class DatabaseService:
    @staticmethod
    def get_all_movies():
        """Lấy danh sách tất cả các phim"""
        try:
            response = supabase.table("movies").select("*").execute()
            print("📦 Dữ liệu movies lấy từ Supabase:", response.data)
            return response.data if response.data else []
        except Exception as e:
            print("❌ Lỗi khi lấy danh sách phim:", str(e))
            return []

    @staticmethod
    def get_movie_by_id(movie_id: int):
        """Lấy thông tin chi tiết 1 bộ phim theo ID"""
        try:
            response = supabase.table("movies").select("*").eq("movie_id", movie_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Lỗi khi lấy phim theo ID {movie_id}:", str(e))
            return None

    @staticmethod
    def create_movie(title: str, description: str = "", is_vip_only: bool = False):
        """Tạo bộ phim mới trực tiếp từ Bot và trả về movie_id"""
        data = {
            "title": title,
            "description": description,
            "is_vip_only": is_vip_only
        }
        try:
            response = supabase.table("movies").insert(data).execute()
            if response.data:
                print("🎉 Tạo phim mới thành công:", response.data)
                return response.data[0]["movie_id"]
            raise Exception("Không nhận được phản hồi dữ liệu từ Supabase sau khi tạo phim.")
        except Exception as e:
            print("❌ Lỗi khi tạo phim mới:", str(e))
            raise e

    @staticmethod
    def get_episodes_by_movie_id(movie_id: int):
        """Lấy danh sách các tập của bộ phim theo movie_id, sắp xếp theo số tập"""
        try:
            response = supabase.table("episodes").select("*").eq("movie_id", movie_id).order("episode_num").execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Lỗi khi lấy tập phim của movie_id {movie_id}:", str(e))
            return []

    @staticmethod
    def get_episode_by_id(episode_id: int):
        """Lấy thông tin 1 tập phim theo episode_id"""
        try:
            response = supabase.table("episodes").select("*").eq("episode_id", episode_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Lỗi khi lấy tập phim theo ID {episode_id}:", str(e))
            return None

    @staticmethod
    def add_episode(movie_id: int, episode_num: int, telegram_file_id: str):
        """Thêm tập phim mới vào database"""
        data = {
            "movie_id": movie_id,
            "episode_num": episode_num,
            "telegram_file_id": telegram_file_id
        }
        try:
            response = supabase.table("episodes").insert(data).execute()
            print("🎉 Thêm tập phim thành công:", response.data)
            return response.data
        except Exception as e:
            print("❌ Lỗi khi thêm tập phim:", str(e))
            raise e