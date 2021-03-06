#!/bin/bash
set -u
set -e

pushd /home/pi

rust_files="$(
    curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | \
    grep -P -o '([A-Za-z0-9_]+/){2}rust-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz'
)"
most_recent_date="$(
    echo ${rust_files} | \
    grep -P -o '201\d-\d\d-\d\d' | \
    sort -n -r | \
    head -n 1
)"
rust_file="$(
    echo ${rust_files} | \
    grep -P -o "([A-Za-z0-9_]+/){2}rust-${most_recent_date}-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz" | \
    head -n 1
)"
url="https://www.dropbox.com/sh/${rust_file}?dl=1"
echo "Downloading $url"
wget "${url}" -O rust.tar.gz
mkdir rust
mv rust.tar.gz rust
pushd rust
tar -xvzf rust.tar.gz --exclude=doc
rm rust.tar.gz
popd

cargo_files="$(
    curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | \
    grep -P -o '([A-Za-z0-9_]+/){2}cargo-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz'
)"
most_recent_date="$(
    echo ${cargo_files} | \
    grep -P -o '201\d-\d\d-\d\d' | \
    sort -n -r | \
    head -n 1
)"
cargo_file="$(
    echo ${cargo_files} | \
    grep -P -o "([A-Za-z0-9_]+/){2}cargo-${most_recent_date}-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz" | \
    head -n 1
)"
url="https://www.dropbox.com/sh/${cargo_file}?dl=1"
echo "Downloading $url"
wget "${url}" -O cargo.tar.gz
mkdir cargo
mv cargo.tar.gz cargo
pushd cargo
tar -xvzf cargo.tar.gz --exclude=doc
rm cargo.tar.gz
popd

set +e
grep -q rust /home/pi/.bashrc
if [ "$?" -ne 0 ];
then
    echo 'Adding rust and cargo to PATH'
    echo 'PATH="${PATH}:/home/pi/rust/bin:/home/pi/cargo/bin"' >> /home/pi/.bashrc
    if [ -z "${LD_LIBRARY_PATH}" ];
    then
        echo 'LD_LIBRARY_PATH="/home/pi/rust/lib/" >> /home/pi/.bashrc
    else
        echo 'LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/home/pi/rust/lib/" >> /home/pi/.bashrc
    fi
fi

popd
