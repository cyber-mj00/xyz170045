# Dayaya Majsoul Stats for 170045.xyz
Majsoul Contest Stats Generator

## Setup
This script is written using Python (Tested working on 3.12).
We recommend that you set up a virtual environment.

To use the script, you need to set up configuration file by changing its name from `config.env.example` to `config.env`, then update the parameters accordingly.

```bash
mv config.env.example config.env
vim config.env
```

You then need to install Python dependencies then run the script.
```bash
pip install -r requirements.txt
```

## Note

This script only works if BOTH Majsoul tourney and [majsoul-api](https://github.com/vg-mjg/majsoul-api "A website for mahjong soul leagues") are set up.

## Thanks

https://github.com/oscarfzs/pymjsoul

https://github.com/Longhorn-Riichi/Ronhorn

https://github.com/vg-mjg/majsoul-api