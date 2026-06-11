from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AI API 配置（兼容 DeepSeek / OpenAI 格式）
    ai_api_key: str = ""
    ai_base_url: str = "https://api.deepseek.com"  # 默认 DeepSeek
    ai_model: str = "deepseek-chat"  # DeepSeek V3

    # 输出目录
    output_dir: str = "output"
    memo_dir: str = "output/memos"

    # 采集配置
    rss_timeout: int = 30  # 请求超时（秒）
    max_articles_per_source: int = 20  # 每个源最多取多少条
    max_total_articles: int = 200  # 单轮最多采集总数
    collect_concurrency: int = 15  # 并行采集数

    # 图片托管配置（用于将本地图片上传到公网图床，使知乎文章能正常显示）
    image_hosting: str = "smms"  # smms / github / none
    # sm.ms API Key（选填，免费版不需要）
    smms_api_key: str = ""
    # GitHub 图床配置（使用 GitHub raw CDN 时需要）
    github_image_repo: str = ""
    github_token: str = ""


settings = Settings()
