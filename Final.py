import io
import os
import re
import sys
import queue
import time
import wave
import threading
import serial
import serial.tools.list_ports
import pyaudio
from pygame import mixer
from concurrent.futures import ThreadPoolExecutor
from google.cloud import speech
from google.cloud import texttospeech
from __future__ import division
from six.moves import queue

Flag = True
Connected = False

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE/10) # 100ms


def Text2Speech(text):
    """Synthesizes speech from the input string of text."""
    client = texttospeech.TextToSpeechClient()

class Speech2Text(object):
    '''Opens a recording stream as
    a generator yielding the audio'''
    def __init__(self, rate, chunk):
        self._rate = rate
        self_chunk = chunk

        # Create a thread-safe buffer of audio data
        self_buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )
        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream,
        into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

def listen_print_loop(responses):
    """ Iterates through server responses and prints them.

        The responses passed is a generator that will block until a response
        is provided by the server.

        Each response may contain multiple results, and each result may contain
        multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
        print only the transcription for the top alternative of the top result.

        In this case, responses are provided for interim results as well. If the
        response is an interim one, print a line feed at the end of it, to allow
        the next result to overwrite it, until the response is a final one. For the
        final one, print a newline to preserve the finalized transcription.
        """
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue


class PlayMP3():

    # Constructor to assign the fileName, which is the mp3 file to play
    def __init__(self, name):
        self._filename = name

    def play(self):
        mixer.init()
        mixer.music.load(self._filename)
        # print("* recording")
        mixer.music.play()
        print("The mp3 should be played")
        while mixer.music.get_busy():  # wait for music to finish playing
            time.sleep(1)
        mixer.music.stop()


class AudiRecorder():  # Audio class based on pyAudio and Wave

    # constructor
    def __init__(self):
        self.open = True
        self.rate = 44100
        self.frames_per_buffer = 1024
        self.channels = 2
        self.format = pyaudio.paInt16
        self.audio_filename = "temp_audio.wav"  # Recording file name
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer=self.frames_per_buffer)
        self.audio_frames = []
        # Audio starts being recorded

    def record(self):

        self.stream.start_stream()
        while (self.open == True):
            data = self.stream.read(self.frames_per_buffer)
            self.audio_frames.append(data)
            if self.open == False:
                break

    # Finishes the audio recording therefore the thread too
    def stop(self):

        if self.open == True:
            self.open = False
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()

            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames))
            waveFile.close()
        pass

    # Launches the audio recording function using a thread
    def start(self):
        audio_thread = threading.Thread(target=self.record)
        print("The recording should start")
        audio_thread.start()


def calling(phonenum):
    port_list = list(serial.tools.list_ports.comports())
    print("A works")
    print(len(port_list))
    if len(port_list) == 0:
        print("nothing to be used")

    else:
        print('D')
        s = serial.Serial(port_list[0].device, timeout=1)
        print('E')
        sio = io.TextIOWrapper(io.BufferedRWPair(s, s))
        print("B works")
        sio.write(f'ATE1\nAT+COLP=1\nATD{str(phonenum)};\n')
        ''' 
        ATE1: 用於設置開啓回顯模式，檢測Module與串口是否連通，能否接收AT命令
        開啓回顯，有利於調試
        
        AT+COLP=1: 開啓被叫號碼顯示，即成功撥通的時候（被叫接聼電話），模塊會
        返回被叫號碼      
        
        ATD電話號碼;:用於撥打電話號碼
        '''
        sio.flush()

        print("G works")
        while 1:
            print(sio.readlines())
            x = ''.join(sio.readlines())
            # print(x)
            if x == '\nNO CARRIER\n':  # Dial failed
                print("Taiwan Can Help")

                break


def str2unicdoe(rawstr):
    result = ''
    for c in rawstr:
        _hex = hex(ord(c))
        if len(_hex) == 4:
            _hex = _hex.replace('0x', '00')
        else:
            _hex = _hex.replace('0x', '')
        result += _hex.upper()
    return result


def textmessage(rawtext, rawphonenum):
    send_test = str2unicdoe(rawtext)
    phonenum = str2unicdoe(rawphonenum)
    port_list = list(serial.tools.list_ports.comports())

    if (len(port_list) == 0):
        print("nothing to be used")

    else:
        s = serial.Serial(port_list[0].device, timeout=1)
        sio = io.TextIOWrapper(io.BufferedRWPair(s, s))
        sio.write(f'AT+CMGF=1\nAT+CSMP=17, 167, 2, 25\nAT+CSCS="UCS2"\nAT+CMGS="{phonenum}"\n')

        '''
        AT+CMGF=1:設置爲文本内容
        AT+CSMP=17, 167, 2, 25:設置文本參數
        AT+CSCS="UCS2":設置爲16位通用8直接倍數編碼字符集  
        '''

        sio.flush()
        print(''.join(sio.readlines()))
        time.sleep(1)
        sio.write(send_test + '\n')
        sio.flush()
        print(''.join(sio.readlines()))
        s.write(b'\x1a')
        sio.flush()
        print(''.join(sio.readlines()))
        s.close()


# Required and wanted processing of final files
def file_manager(filename):
    local_path = os.getcwd()

    if os.path.exists(str(local_path) + "/temp_audio.wav"):
        os.remove(str(local_path) + "/temp_audio.wav")


def main():

    executor = ThreadPoolExecutor(max_workers=16)

    # thread for phone call
    executor.submit(calling, 94030591)

    # Start audio recording
    audio_thread = AudiRecorder()
    executor.submit(audio_thread.start(), )

    # thread for playing the music
    pl = PlayMP3('01.mp3')
    executor.submit(pl.play())

    # Sleep for 10 seconds
    # time.sleep(10)

    # Stop audio recording
    executor.submit(audio_thread.stop)

    print("Done")
    exit()


if __name__ == "__main__":
    main()
