#!/usr/bin/env python3

import sys
import argparse
from struct import unpack
from collections import namedtuple
import os


class Ext4(object):
    __SUPERBLOCK_PACK__ = "<IIIIIIIIIIIIIHHHHHHIIIIHHIHHIII16s16s64sI"
    __GROUP_DESCRIPTOR_PACK__ = "<IIIHHHHIHHHH"
    __INODE_PACK__ = "<HHIIIIIHHII4s60sIIII12s"
    __EXTENT_HEADER_PACK__ = "<HHHHI"
    __EXTENT_INDEX_PACK__ = "<IIHH"
    __EXTENT_ENTRY_PACK__ = "<IHHI"
    __DIR_ENTRY_PACK__ = "<IHH"
    __DIR_ENTRY_V2_PACK__ = "<IHBB"

    __SuperBlock__ = namedtuple('Ext4SuperBlock', """
        s_inodes_count
        s_blocks_count_lo
        s_r_blocks_count_lo
        s_free_blocks_count_lo
        s_free_inodes_count
        s_first_data_block
        s_log_block_size
        s_log_cluster_size
        s_blocks_per_group
        s_clusters_per_group
        s_inodes_per_group
        s_mtime
        s_wtime
        s_mnt_count
        s_max_mnt_count
        s_magic
        s_state
        s_errors
        s_minor_rev_level
        s_lastcheck
        s_checkinterval
        s_creator_os
        s_rev_level
        s_def_resuid
        s_def_resgid
        s_first_ino
        s_inode_size
        s_block_group_nr
        s_feature_compat
        s_feature_incompat
        s_feature_ro_compat
        s_uuid
        s_volume_name
        s_last_mounted
        s_algorithm_usage_bitmap
    """)

    __GroupDescriptor__ = namedtuple('Ext4GroupDescriptor', """
        bg_block_bitmap_lo
        bg_inode_bitmap_lo
        bg_inode_table_lo
        bg_free_blocks_count_lo
        bg_free_inodes_count_lo
        bg_used_dirs_count_lo
        bg_flags
        bg_exclude_bitmap_lo
        bg_block_bitmap_csum_lo
        bg_inode_bitmap_csum_lo
        bg_itable_unused_lo
        bg_checksum
    """)

    __Inode__ = namedtuple('Ext4Inode', """
        i_mode
        i_uid
        i_size_lo
        i_atime
        i_ctime
        i_mtime
        i_dtime
        i_gid
        i_links_count
        i_blocks_lo
        i_flags
        i_osd1
        i_block
        i_generation
        i_file_acl_lo
        i_size_high
        i_obso_faddr
        i_osd2
    """)

    __ExtentHeader__ = namedtuple('Ext4ExtentHeader', """
        eh_magic
        eh_entries
        eh_max
        eh_depth
        eh_generation
    """)

    __ExtentIndex__ = namedtuple('Ext4ExtentIndex', """
        ei_block
        ei_leaf_lo
        ei_leaf_hi
        ei_unused
    """)

    __ExtentEntry__ = namedtuple('Ext4ExtentEntry', """
        ee_block
        ee_len
        ee_start_hi
        ee_start_lo
    """)

    __DirEntry__ = namedtuple('Ext4DirEntry', """
        inode
        rec_len
        name_len
    """)

    __DirEntryV2__ = namedtuple('Ext4DirEntryV2', """
        inode
        rec_len
        name_len
        file_type
    """)

    class DirEntry:
        def __init__(self, inode=0, name=None, type=0):
            self._inode = inode
            self._name = name
            self._type = type

        def __str__(self):
            entry_type = [
                "Unknown",
                "Regular file",
                "Directory",
                "Character device file",
                "Block device file",
                "FIFO",
                "Socket",
                "Symbolic link"
            ][self._type]
            return "{name:24} ({type}, inode {inode})".format(inode=self._inode, name=self._name, type=entry_type)

        @property
        def inode(self):
            return self._inode

        @property
        def name(self):
            return self._name

        @property
        def type(self):
            return self._type

        @inode.setter
        def inode(self, x):
            self._inode = x

        @name.setter
        def name(self, x):
            self._name = x

        @type.setter
        def type(self, x):
            self._type = x

    def __init__(self, filename=None):
        self._ext4 = None
        self._superblock = None
        self._block_size = 1024

        if filename is not None:
            self.load(filename)

    def __str__(self):
        if self._superblock is None:
            return "Not loaded"
        else:
            volume_name = self._superblock.s_volume_name.decode('utf-8').rstrip('\0')
            mounted_at = self._superblock.s_last_mounted.decode('utf-8').rstrip('\0')
            if not mounted_at:
                mounted_at = "not mounted"
            return "Volume name: {}, last mounted at: {}".format(volume_name, mounted_at)

    def _read_group_descriptor(self, bg_num):
        gdt_offset = (self._superblock.s_first_data_block + 1) * self._block_size + (bg_num * 64)
        self._ext4.seek(gdt_offset)
        return self.__GroupDescriptor__._make(unpack(self.__GROUP_DESCRIPTOR_PACK__, self._ext4.read(32)))

    def _read_inode(self, inode_num):
        inode_bg_num = (inode_num - 1) // self._superblock.s_inodes_per_group
        bg_inode_idx = (inode_num - 1) % self._superblock.s_inodes_per_group
        group_desc = self._read_group_descriptor(inode_bg_num)
        inode_offset = \
            (inode_bg_num * self._superblock.s_blocks_per_group * self._block_size) \
            + (group_desc.bg_inode_table_lo * self._block_size) + (bg_inode_idx * self._superblock.s_inode_size)
        self._ext4.seek(inode_offset)
        return self.__Inode__._make(unpack(self.__INODE_PACK__, self._ext4.read(128))), inode_bg_num

    def _read_extent(self, data, bg, extent_block):
        hdr = self.__ExtentHeader__._make(unpack(self.__EXTENT_HEADER_PACK__, extent_block[:12]))
        if hdr.eh_magic != 0xf30a:
            raise RuntimeError("Bad extent magic")

        for eex in range(0, hdr.eh_entries):
            raw_offset = 12 + (eex * 12)
            entry_raw = extent_block[raw_offset:raw_offset + 12]
            if hdr.eh_depth == 0:
                entry = self.__ExtentEntry__._make(unpack(self.__EXTENT_ENTRY_PACK__, entry_raw))
                self._ext4.seek((bg * self._superblock.s_blocks_per_group + entry.ee_start_lo) * self._block_size)
                data += self._ext4.read(self._block_size * entry.ee_len)
            else:
                index = self.__ExtentIndex__._make(unpack(self.__EXTENT_INDEX_PACK__, entry_raw))
                self._ext4.seek((bg * self._superblock.s_blocks_per_group + index.ei_leaf_lo) * self._block_size)
                lower_block = self._ext4.read(self._block_size)
                data = self._read_extent(data, bg, lower_block)

        return data

    def _read_data(self, bg, inode):
        data = b''

        if inode.i_size_lo == 0:
            pass
        elif inode.i_flags & 0x10000000 or (inode.i_mode & 0xf000 == 0xa000 and inode.i_size_lo <= 60):
            data = inode.i_block
        elif inode.i_flags & 0x80000:
            data = self._read_extent(data, bg, inode.i_block)
        else:
            raise RuntimeError("Mapped Inodes is not supported")

        return data

    def load(self, filename):
        self._ext4 = open(filename, "rb")
        self._ext4.seek(1024)
        self._superblock = self.__SuperBlock__._make(unpack(self.__SUPERBLOCK_PACK__, self._ext4.read(204)))
        if self._superblock.s_magic != 0xef53:
            raise RuntimeError("Bad superblock magic")
        self._block_size = 2 ** (10 + self._superblock.s_log_block_size)

    def read_dir(self, inode_num):
        inode, bg = self._read_inode(inode_num)
        # noinspection PyTypeChecker
        dir_raw = self._read_data(bg, inode)
        dir_data = list()
        offset = 0
        while offset < len(dir_raw):
            entry_raw = dir_raw[offset:offset + 8]
            entry = self.DirEntry()
            if self._superblock.s_feature_incompat & 0x2:
                dir_entry = self.__DirEntryV2__._make(unpack(self.__DIR_ENTRY_V2_PACK__, entry_raw))
                entry.type = dir_entry.file_type
            else:
                dir_entry = self.__DirEntry__._make(unpack(self.__DIR_ENTRY_PACK__, entry_raw))
                entry_inode = self._read_inode(dir_entry.inode)
                inode_type = entry_inode.i_mode & 0xf000
                if inode_type == 0x1000:
                    entry.type = 5
                elif inode_type == 0x2000:
                    entry.type = 3
                elif inode_type == 0x4000:
                    entry.type = 2
                elif inode_type == 0x6000:
                    entry.type = 4
                elif inode_type == 0x8000:
                    entry.type = 1
                elif inode_type == 0xA000:
                    entry.type = 7
                elif inode_type == 0xC000:
                    entry.type = 6
            entry.inode = dir_entry.inode
            entry.name = dir_raw[offset + 8:offset + 8 + dir_entry.name_len].decode('utf-8')
            dir_data.append(entry)
            offset += dir_entry.rec_len
        return dir_data

    def read_file(self, inode_num):
        inode, bg = self._read_inode(inode_num)
        # noinspection PyTypeChecker
        return self._read_data(bg, inode)[:inode.i_size_lo], inode.i_atime, inode.i_mtime

    def read_link(self, inode_num):
        inode, bg = self._read_inode(inode_num)
        # noinspection PyTypeChecker
        return self._read_data(bg, inode).decode('utf-8')[:inode.i_size_lo]

    @property
    def root(self):
        return self.read_dir(2)


class Application(object):
    def __init__(self):
        self._args = None
        self._ext4 = None

    def _parse_args(self):
        parser = argparse.ArgumentParser()

        parser.add_argument("-v", "--verbose", dest='verbose', help="verbose output",
                            action='store_true')
        parser.add_argument("-D", "--directory", dest='directory', type=str, help="set output directory", default=".")
        parser.add_argument("filename", type=str, help="EXT4 device or image")

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--save-symlinks", help="save symlinks as is (default)", action='store_true')
        group.add_argument("--text-symlinks", help="save symlinks as text file", action='store_true')
        group.add_argument("--empty-symlinks", help="save symlinks as empty file", action='store_true')
        group.add_argument("--skip-symlinks", help="do not save symlinks", action='store_true')

        try:
            self._args = parser.parse_args()
        except SystemExit:
            sys.exit(2)

    def _extract_dir(self, dir_data, path, name=None):
        assert self._ext4 is not None
        if name is not None:
            path = os.path.join(path, name)
        try:
            os.mkdir(path)
        except FileExistsError:
            pass

        for de in dir_data:
            if de.type == 1:  # regular file
                data, atime, mtime = self._ext4.read_file(de.inode)
                file = open(os.path.join(path, de.name), 'w+b')
                file.write(data)
                file.close()
                os.utime(file.name, (atime, mtime))
            elif de.type == 2:  # directory
                if de.name == '.' or de.name == '..':
                    continue
                self._extract_dir(self._ext4.read_dir(de.inode), path, de.name)
            elif de.type == 7:  # symlink
                if self._args.skip_symlinks:
                    continue
                link = os.path.join(path, de.name)
                link_to = self._ext4.read_link(de.inode)
                if self._args.text_symlinks:
                    link = open(link, "w+b")
                    link.write(link_to.encode('utf-8'))
                    link.close()
                elif self._args.empty_symlinks:
                    open(link, "w+").close()
                else:
                    os.symlink(link_to, link + ".tmp")
                    os.rename(link + ".tmp", link)

    def _do_extract(self):
        self._ext4 = Ext4(self._args.filename)
        self._extract_dir(self._ext4.root, self._args.directory)

    def run(self):
        self._parse_args()
        self._do_extract()


if __name__ == '__main__':
    app = Application()
    app.run()
