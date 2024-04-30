from pydub import AudioSegment
import os
import time


def convert_mp3_to_wav(mp3_file: str) -> str | None:
    """Check if the file has the .mp3 extension

    Args:
        mp3_file (str): The path to the MP3 file to be converted.

    Returns:
        str | None: The path to the converted WAV file, or None if the input file
                    does not have an '.mp3' extension.
    """
    if mp3_file.endswith('.mp3'):
        wav_file = os.path.splitext(mp3_file)[0] + '.wav'
        audio = AudioSegment.from_mp3(mp3_file)
        audio.export(wav_file, format="wav")
        return wav_file
    else:
        return None


def audio_process(input_filename: str) -> str:
    """Process an audio file to trim  the audio to a maximum duration
    of 4000 milliseconds and add a timestamp to the filename. 
    This function handles both MP3 and WAV files.

    Args:
        input_filename (str): The path to the input audio file (either MP3 or WAV).

    Returns:
        str: The path to the processed and trimmed WAV file.
    """
    #
    if input_filename.endswith('.mp3'):
        input_filename = convert_mp3_to_wav(input_filename)
    audio = AudioSegment.from_wav(input_filename)
    timestamp_ns = str(time.time_ns())
    output_filename = os.path.splitext(input_filename)[
        0] + '_' + timestamp_ns + '.wav'
    max_duration = 4000
    start_time = 0
    end_time = min(max_duration, len(audio))
    segment = audio[start_time:end_time]
    segment.export(output_filename, format="wav")
    return output_filename
