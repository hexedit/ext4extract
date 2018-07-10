"""
    ext4extract - Ext4 data extracting tool
    Copyright (C) 2017, HexEdit (IFProject)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


class Metadata:
    def __init__(self, inode, itype, size, ctime, mtime, uid=0, gid=0, mode=0):
        self._inode = inode
        self._type = itype
        self._size = size
        self._ctime = ctime
        self._mtime = mtime
        self._uid = uid
        self._gid = gid
        self._mode = mode

    def __str__(self):
        # TODO fixed list, format mode, extended attributes
        return "{_type} {_size} {_ctime} {_mtime} {_uid} {_gid} {_mode}".format(**vars(self))
