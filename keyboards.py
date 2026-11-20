def quality_keyboard(url):
    return {
        "inline_keyboard": [
            [
                {"text": "144p", "callback_data": f"144|{url}"},
                {"text": "240p", "callback_data": f"240|{url}"},
                {"text": "360p", "callback_data": f"360|{url}"}
            ],
            [
                {"text": "480p", "callback_data": f"480|{url}"},
                {"text": "720p", "callback_data": f"720|{url}"},
                {"text": "1080p", "callback_data": f"1080|{url}"}
            ],
            [
                {"text": "أفضل جودة متاحة", "callback_data": f"best|{url}"}
            ],
            [
                {"text": "استخراج الصوت فقط 🎵", "callback_data": f"audio|{url}"}
            ]
        ]
    }
