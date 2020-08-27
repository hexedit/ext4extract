**Ext4 data extracting tool**

Currently supports only 32-bit ext4, using extents, extracts only files/directories and symlinks with various options.
*Mapped* file blocks are **not** supported.

usage
-----

`ext4extract.py [-h] [-v] [-D DIRECTORY] [-S SYMLINKS] [-M METADATA]
                      [--save-symlinks | --text-symlinks | --empty-symlinks | --skip-symlinks]
                      filename`

**positional arguments:**

* **filename** - EXT4 device or image

**optional arguments:**

* **-h, --help** - show this help message and exit

* **-v, --verbose** - verbose output

* **-D DIRECTORY, --directory DIRECTORY** - set output directory

* **-S SYMLINKS, --dump-symlink-table SYMLINKS** - generate symlink table

* **-M METADATA, --dump-metadata METADATA** - generate inode metadata table (including extended attributes)

* **Symlink options (mutually-exclusive)**

  * **--save-symlinks** - save symlinks as is (default)

  * **--text-symlinks** - save symlinks as text file

  * **--empty-symlinks** - save symlinks as empty file

  * **--skip-symlinks** - do not save symlinks
