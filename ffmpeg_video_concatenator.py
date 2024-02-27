import os  
import subprocess 
import threading 
import shutil  
from tkinter import filedialog  
import ttkbootstrap as ttks
from ttkbootstrap.dialogs import Messagebox
import darkdetect
import sys

INITIAL_PROGRESS = 10
PROGRESS_INCREMENT = 80
END_PROGRESS = 100
AAC = 'aac'
H264 = 'libx264'
AUDIO = 2

class VideoConverterApp():  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = ttks.Window()
        self.style = ttks.Style()
        self.init_ui()
 
    def init_ui(self):
        self.change_theme()
        self.app.title("Concatenation")
        self.app.geometry("400x300")  
        self.files = []  
        self.output = ''  
        self.converted_files = [] 
        self.title = ttks.Label(self.app, text="Choose files to merge",  font=("cursive", 20), foreground="#0070ff")
        self.title.pack(padx=10, pady=10)
        choose_files_button = ttks.Button(self.app, text='Choose Files', command=self.choose_files, width=20)  
        choose_files_button.pack(padx=10, pady=10)  
        save_to_button = ttks.Button(self.app, text='Save Output To', command=self.save_to, width=20)  
        save_to_button.pack(padx=10, pady=10)  
        merge_button = ttks.Button(self.app, text='Merge Files', command=self.start_merge, width=20)  
        merge_button.pack(padx=10, pady=10)  
        self.progress = ttks.Label(self.app, text="")
        self.progress.pack(padx=10, pady=10)
        self.progress_bar = ttks.Progressbar(self.app, length=300, mode='determinate')  
        self.progress_bar.pack(padx=10, pady=10)  
        
    def choose_files(self):  
        self.files = list(filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4;*.ts;*.avi;*.mkv;*.flv")]))    
        print(self.files)

    def save_to(self): 
        self.output = filedialog.asksaveasfilename(defaultextension=".mp4") 
        print(self.output)

    def start_merge(self): 
        if not self.files or not self.output:  
            self.progress_bar['value'] = 100
            self.progress_bar.configure(bootstyle="warning")
            Messagebox.show_warning("Please choose files and output location first.","Warning")
            return      
        confirm = Messagebox.show_question(
            "Are you sure you want to merge the following files? : " 
            + ", ".join(os.path.basename(file) for file in self.files)  
            + "\t\nThe merged file will be saved as:\n" 
            + self.output, "Confirmation"
        )  

        if confirm == "Yes": 
            threading.Thread(target=self._start_merge).start()
            self.title.configure(text="")  
        else:
            self.files = []  
            self.output = '' 
            self.title.configure(text="Choose files to merge")

    def _start_merge(self):
        try: 
            self.check_requirements()
            self.get_video_specs()
            self.process_files()
            self.finalize_merge()
            self.cleanup_after_merge()
        except Exception as e:  
            self.handle_merge_error(e)
            self.cleanup_after_merge()
            
    def check_requirements(self):
        if not (shutil.which('ffmpeg') and shutil.which('ffprobe')):  
            raise Exception ("ffmpeg and ffprobe are required but not installed or not in the PATH.")

    def get_video_specs(self):
        self.progress_bar.configure(bootstyle="default")
        for video_file in self.files:  
            try:
                width, height, fps, audio_hz, time_base = self.get_video_info(video_file)
                if (width != "N/A" and height != "N/A"  and fps != "N/A" and audio_hz != "N/A" and time_base != "N/A"):
                    if  width <=720 and height <=480:
                        SAR = '3/2'
                        DAR = '4/3'          
                    elif width >= 1280 and height >= 720:
                        SAR = '1/1'
                        DAR = '16/9'
                    else:
                        SAR = '1/1'
                        DAR = '16/9'                        
                    return int(width), int(height), fps, int(audio_hz), int(time_base), str(SAR),str(DAR)
            except Exception as e:
                self.handle_merge_error(e)
                print(f"Error in get_video_specs {e}")
        raise Exception("No valid video file found.")

    def get_video_info(self, video_file):  
        try:
            cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,time_base -of csv=s=x:p=0 "{video_file}"'  
            output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip().split('\n')[0].split('x') 
            width, height, fps, time_base = output[0], output[1], output[2], output[3].split('/')[1]
            cmd = f'ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "{video_file}"'  
            audio_hz = subprocess.check_output(cmd, shell=True).decode('utf-8').strip().split('\n')[0]
            return int(width), int(height),fps, int(audio_hz), int(time_base) 
        except Exception as e:
            print(f"Error in get_video_info {e}")
            self.handle_merge_error(e)
            return None, None, None, None, None

    def process_files(self):
        width, height, fps, audio_hz, time_base, SAR, DAR = self.get_video_specs()
        self.progress_bar['value'] = INITIAL_PROGRESS
        self.progress.configure(text=f"Merging in process - {self.progress_bar['value']}%", font=("cursive", 16), foreground="#0070ff")
        for i, video_file in enumerate(self.files, start=1):  
            try:
                output_file = f"input{i}.mp4"
                self.convert_video(video_file, output_file, width, height, str(fps), audio_hz, time_base, str(SAR),str(DAR))  
                self.converted_files.append(output_file)  
                print(f"File {output_file} was not skipped")
            except Exception as e:
                self.handle_merge_error(e)
                print(f"Error in process_files {e}")
            self.progress_bar['value'] += PROGRESS_INCREMENT/len(self.files)  
            self.progress.configure(text=f"Merging in process - {round(self.progress_bar['value'])}%", font=("cursive", 16), foreground="#0070ff")
            self.app.update_idletasks()
    
    def finalize_merge(self):
        try:
            with open('list.txt', 'w') as f: 
                for video_file in self.converted_files:  
                    f.write(f"file '{video_file}'\n") 
             
            self.merge_videos(self.output)
            self.progress_bar['value'] = 100  
            self.progress_bar.configure(bootstyle="success")
            self.progress.configure(text=f"Merging done - {self.progress_bar['value']}%", font=("cursive", 16), foreground="#0070ff")
            self.app.update_idletasks()  
            self.progress.configure(text="Merging done ", foreground="#28b62c")
        except Exception as e:
            self.handle_merge_error(e)
            print(f"Error in finalize_merge {e}")

    def convert_video(self, input_file, output_file, width, height, fps, audio_hz, time_base, SAR, DAR): 
        try:
            cmd = f'ffmpeg -y -i "{input_file}" -vf "scale={width}:{height}, setsar={SAR}, setdar={DAR}" -r {fps} -ar {audio_hz} -ac {AUDIO} -video_track_timescale {time_base} -c:v {H264} -c:a {AAC} "{output_file}"'  
            subprocess.call(cmd, shell=True)   
            print(f"Converted video file: {input_file}")
        except Exception as e:
            self.handle_merge_error(e)
            print(f"Error in convert_video {e}")

    def merge_videos(self, output_file):  
        try:
            cmd = f'ffmpeg -y -f concat -safe 0 -i list.txt -c copy "{output_file}"'  
            subprocess.check_output(cmd, shell=True)  
            self.app.update_idletasks()  
        except Exception as e:
            self.handle_merge_error(e)
            print(f"Error in merge_video {e}")

    def handle_merge_error(self,e):
        self.app.after(0, lambda: Messagebox.show_error(f"Error: {str(e)}", "Error")) 
        print(f"Error: {str(e)}") 
        self.progress.configure(text="An error occured during merging ", foreground="#ff0800")
        self.progress_bar['value'] = END_PROGRESS
        self.progress_bar.configure(bootstyle="danger")
        sys.exit(1)
    
    def cleanup_after_merge(self):
        try:
            self.delete_converted_files()  
            print("Files merged")
            self.app.after(0, lambda: Messagebox.show_info(
                "Files: merged into:\n"
                + self.output,
                "Files merged successfully!", 
                alert=True,
            ))  
            self.title.configure(text="Choose files to merge",  font=("cursive", 20), foreground="#0070ff")
        except Exception as e:
            self.handle_merge_error(e)

    def delete_converted_files(self): 
        try: 
            for file in self.converted_files:  
                os.remove(file)
            if os.path.exists('list.txt'):  
                os.remove('list.txt') 
            self.converted_files = [] 
        except Exception as e:
            print(f"Error in delete_converted_files {e}")

    def change_theme(self):
        theme = 'cyborg' if darkdetect.isDark() else 'lumen'  
        self.style.theme_use(theme)  

if __name__ == "__main__":  
    VideoConverterApp().app.mainloop()  