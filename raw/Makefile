setup: FORCE
	sudo apt-get update
	sudo apt-get install python3-venv python3-tk

venv: FORCE
	python3 -m venv ~/.venv/susam.in
	echo . ~/.venv/susam.in/bin/activate > venv
	. ./venv && pip install matplotlib

hearts:
	. ./venv && python3 hearts.py
	cp heart-cardoid.png ../static/files/blog

clumsy-equations: clean
	. ./venv && python clumsy-equations.py
	cp clumsy-equations-1.png ../static/files/blog
	cp clumsy-equations-2.png ../static/files/blog

channel-capacity: clean
	. ./venv && python channel-capacity.py
	cp clumsy-capacity.png ../static/files/blog

dosbox-logo: clean
	# PNGs
	convert logo_000.png -sample '640x480!' dosbox-logo-0.png
	convert logo_001.png -sample '640x480!' dosbox-logo-1.png
	# MP4
	ffmpeg -i logo_000.avi -an -c:v libx264 -crf 17 -preset veryslow \
	       -pix_fmt yuv420p -vf scale=640:480:flags=neighbor \
	       dosbox-logo-circles.mp4
	# GIF
	ffmpeg -i logo_000.avi -vf palettegen palette.png
	ffmpeg -i logo_000.avi -i palette.png \
	       -lavfi 'fps=30,scale=640:480:flags=neighbor,paletteuse' \
	       dosbox-logo-circles.gif
	# Copy
	cp dosbox-logo-0.png ../static/files/blog
	cp dosbox-logo-1.png ../static/files/blog
	cp dosbox-logo-circles.mp4 ../static/files/blog
	cp dosbox-logo-circles.gif ../static/files/blog

view:
	for f in *.png; do xdg-open "$$f"; done

clean:
	# Clumsy Equations
	rm -f clumsy-equations-1.png
	rm -f clumsy-equations-2.png
	# When Worse is Better
	rm -f channel-capacity.png
	# Good Quality DOSBox Video Capture
	rm -f dosbox-logo-0.png
	rm -f dosbox-logo-1.png
	rm -f dosbox-logo-circles.mp4
	rm -f dosbox-logo-circles.gif
	rm -f palette.png

FORCE:
