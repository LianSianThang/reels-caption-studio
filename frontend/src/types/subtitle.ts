export interface Word {
  text: string;
  start: number;
  end: number;
}

export interface SubtitleSegment {
  id: number;
  start: number;
  end: number;
  source_text?: string;
  text: string;
  words?: Word[];
}

export interface VideoMetadata {
  video_id: string;
  filename: string;
  video_url: string;
  duration: number;
  width: number;
  height: number;
  aspect_ratio: "9:16" | "1:1" | "16:9";
}

export interface StyleSettings {
  aspect_ratio: "9:16" | "1:1" | "16:9";
  font_name: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  outline_color: string;
  bg_color: string;
  style_preset: "karaoke" | "neon_box" | "minimal";
  position: "bottom" | "center" | "top";
}
