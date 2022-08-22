# CityMaps

![Logo](/assets/logo.png)

## How To
1. Andare su prettymaps nel file main mattere il nome della citta desiderata a riga 18 (e a 90 e 91 il nome con cui si vogliono salvare i file)

2. andare nel progetto citymaps (questo) e fare una copia del file template.html e rinominarlo ad esempio col nome della citta che si sta facendo

3. aprire il file svg e copiare dal tag svg in poi

4. incollare nel file nome_citta.html nel punto indicato il codice svg \
```sed -e '/here goes svg/r./palmanova.svg' test-template.html > palmanova.html```

5. aggiungere il css con l'animazione \
```sed -e '/\/svg>/r./pcsstouse.txt' palmanova.html > palmanova.html```

6. aprire nel browser il file nome_citta.html

7. alla fine dell'animazione verra chiesto dove si vuole salvare il video

8. tradurlo in mp4\
```ffmpeg -fflags +genpts -i videos/first/macao.webm -r 24 videos/first/macao.mp4```

9. run command ```python generate.py ``` per generare un pezzo di video con l'immagine completa e colorata

10. run command ```python mergevideos.py ``` per mergiare i due video insieme

11. vai su tiktok, pubblica, make profit