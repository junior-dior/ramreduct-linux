#!/bin/sh
# Build the .deb:  ./build-deb.sh   ->  build/ramreduct-linux_2.0.0_all.deb
set -e
cd "$(dirname "$0")"
V=2.0.0
B=build/pkg
rm -rf build; mkdir -p $B/DEBIAN $B/usr/bin $B/usr/share/ramreduct $B/usr/lib/ramreduct \
  $B/usr/share/polkit-1/actions $B/usr/share/applications $B/usr/share/icons/hicolor/scalable/apps
install -m755 ramreduct.py $B/usr/share/ramreduct/ramreduct.py
install -m755 ramreduct-helper $B/usr/lib/ramreduct/ramreduct-helper
install -m644 org.ramreduct.policy $B/usr/share/polkit-1/actions/org.ramreduct.policy
install -m644 ramreduct.desktop $B/usr/share/applications/ramreduct.desktop
install -m644 ramreduct.svg $B/usr/share/icons/hicolor/scalable/apps/ramreduct.svg
printf '#!/bin/sh\nexec python3 /usr/share/ramreduct/ramreduct.py "$@"\n' > $B/usr/bin/ramreduct
chmod 755 $B/usr/bin/ramreduct
cat > $B/DEBIAN/control <<EOC
Package: ramreduct-linux
Version: $V
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-3.0, gir1.2-pango-1.0, pkexec | policykit-1
Recommends: fonts-inter | fonts-noto-core, fonts-noto-core
Maintainer: 4133F DEV. <noreply@localhost>
Homepage: https://github.com/junior-dior
Description: RAM Reduct for Linux - memory cleaner with dark GUI
 Memory cleaner similar to Mem Reduct on Windows. Drops caches, trims
 process memory, compacts memory and cycles swap, with auto-clean.
EOC
printf '#!/bin/sh\nset -e\ngtk-update-icon-cache -f -q /usr/share/icons/hicolor 2>/dev/null || true\nupdate-desktop-database -q 2>/dev/null || true\nexit 0\n' > $B/DEBIAN/postinst
chmod 755 $B/DEBIAN/postinst
dpkg-deb --root-owner-group --build $B build/ramreduct-linux_${V}_all.deb
echo "OK -> build/ramreduct-linux_${V}_all.deb"
