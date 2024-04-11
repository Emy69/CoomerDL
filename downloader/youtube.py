from pytube import YouTube

class YouTubeDownloader:
    def __init__(self, url):
        self.url = url
        self.yt = YouTube(url)
        
    def get_video_info(self):
        """Obtiene información básica del video."""
        video_info = {
            "title": self.yt.title,
            "channel": self.yt.author,
        }
        return video_info
    
    def download_video(self, path='./'):
        """Descarga el video en la mejor resolución disponible."""
        video_stream = self.yt.streams.get_highest_resolution()
        if video_stream:
            video_info = self.get_video_info()
            video_stream.download(output_path=path)
            return f"Video descargado: {video_info['title']} por {video_info['channel']} en {path}"
        else:
            return "Error: No se pudo encontrar el stream del video."
