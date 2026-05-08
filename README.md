```
  _____                    ____  _     
 |  ___|_ _ _ __  ______ _|  _ \| |    
 | |_ / _` | '_ \|_  / _` | | | | |    
 |  _| (_| | | | |/ / (_| | |_| | |___ 
 |_|  \__,_|_| |_/___\__,_|____/|_____|  
```

### What is this?
This tool is designed to get m3u8 stream URLs to content you own or rent on Fanza (dmm.co.jp).  
NOTE: This tool does not make it possible to watch content you do not own or rent, and you must have it available in your library for you to be able to access it.

### How do I use this?
To get started, follow these steps.
1. Install python if you haven't already. During the installation, do not forget to tick the `Add python to PATH` checkbox.
2. Install the `requests` library, by running the following in your terminal / command line: `pip install requests`
3. Download [this project as a zip](https://github.com/PicoQubit/FanzaDL/archive/refs/heads/main.zip) and unzip it or get it via `git clone`.
4. Open a terminal inside or navigate to the folder containing the source code.
5. Run `python main.py`, the login procedure should start, use your regular DMM/Fanza credentials.
6. Once logged in, select which items you would like to download by entering a number. Use `,` to separate values, `-` for ranges and `*` to get everything.
7. The tool will give you a list of m3u8 URLs to unencrypted streams to the selected content. This should be given to a tool like [n-m3u8dl-re](https://github.com/nilaoda/N_m3u8DL-RE), [ffmpeg](https://www.ffmpeg.org/), or [jdownloader](https://jdownloader.org/).

### FAQ

##### Why am I getting 404 while downloading the stream?
DMM is extremely protective of their content. This can either happen due to a non-residential IP (Datacenter or VPN), or due to rate limiting. I've found the default thread count employed by n-m3u8dl-re to be triggering this error, instead finding a thread count of 4 or 2 to be much more stable.

##### How do I select the quality I would like to download
There is no quality selection on purpose, as the generated URLs provide you with all the available qualities. A proper downloading tool will ask you which quality you would like to download before proceeding. The only notable exception is VR content which works slightly differently, see the question below.

##### Does this tool support VR content?
Yes, absolutely! It is able to extract 8K VR streams, at the maximum available bitrate. Unfortunately, VR stream URLs do not provide you with all available qualities at once. These are divided into 3 groups: medium, high and 8k. You will find the following qualities in each
- **medium**: 4000 (3840x1920@4000kbps), 6000 (3840x1920@6000kbps), 12000 (3840x1920@12000kbps)
- **high**: hq (5400x2700@15000kbps), uhq (5400x2700@19000kbps)
- **8k** (if provided): 8192x4096@15000kbps, 8192x4096@230000kbps, 8192x4096@350000kbps

Selecting between each can be done by using the `--vr-quality` flag.

##### Can I automate this?
Yes! Special flags were added which allow you to output the URLs to a given file. Additionally, the tool can output a CSV for containing the content ID and part for each URL, which is useful if you would like to write a script for invoking the downloader. If you would like more information, make use of the `--help` flag.

##### Is this tool safe?
I do not provide any guarantees for the safety of your account by using this tool. Redistributing copyrighted content is illegal and I do not endorse it.
