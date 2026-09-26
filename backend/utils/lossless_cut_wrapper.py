import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger(__name__)


class LosslessCutWrapper:
    """Wrapper for lossless-cut operations using ffmpeg.
    
    lossless-cut is a tool for lossless video/audio editing. This wrapper
    provides similar functionality using ffmpeg commands when lossless-cut
    is not available as a library.
    """
    
    @staticmethod
    def trim_video_lossless(
        input_path: Path,
        start_time: float,
        end_time: float,
        output_path: Path,
        codec: str = "copy"
    ) -> bool:
        """Trim video using lossless operations when possible.
        
        Args:
            input_path: Input video path
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Output video path
            codec: Video codec to use ('copy' for stream copy, 'libx264' for re-encode)
            
        Returns:
            Whether the operation succeeded
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            ffmpeg_bin = get_ffmpeg_path()
            duration = end_time - start_time
            
            # Use stream copy for true lossless when codec is 'copy'
            # Otherwise re-encode with specified codec
            cmd = [
                ffmpeg_bin,
                '-ss', str(start_time),
                '-i', str(input_path),
                '-t', f'{duration:.3f}',
                '-c:v', codec,
                '-c:a', 'copy' if codec == 'copy' else 'aac',
                '-b:a', '128k',
                '-avoid_negative_ts', 'make_zero',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                logger.info(f"成功使用 lossless 方式剪辑视频: {start_time}s -> {end_time}s")
                return True
            else:
                logger.error(f"Lossless剪辑失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Lossless剪辑异常: {e}")
            return False
    
    @staticmethod
    def join_videos_lossless(
        video_paths: List[Path],
        output_path: Path,
        codec: str = "libx264"
    ) -> bool:
        """Join multiple videos losslessly using ffmpeg concat.
        
        Args:
            video_paths: List of video paths to join
            output_path: Output video path
            codec: Video codec to use
            
        Returns:
            Whether the operation succeeded
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not video_paths:
                logger.error("没有要连接的视频片段")
                return False
            
            # Create concat file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                file_list_path = temp_path / "file_list.txt"
                
                with open(file_list_path, 'w', encoding='utf-8') as f:
                    for video_path in video_paths:
                        if video_path.exists():
                            # Use absolute path
                            abs_path = video_path.resolve()
                            f.write(f"file '{abs_path}'\n")
                
                ffmpeg_bin = get_ffmpeg_path()
                cmd = [
                    ffmpeg_bin,
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(file_list_path),
                    '-c:v', codec,
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    str(output_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                
                if result.returncode == 0:
                    logger.info(f"成功连接 {len(video_paths)} 个视频片段")
                    return True
                else:
                    logger.error(f"视频连接失败: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"视频连接异常: {e}")
            return False