#!/usr/bin/env python3

import sys
import argparse
from struct import unpack
from collections import namedtuple


class Ext4:
    __SUPERBLOCK_PACK__ = "<IIIIIIIIIIIIIHHHHHHIIIIHHIHHIII16s16s64sI"
    __GROUP_DESCRIPTOR_PACK__ = "<IIIHHHHIHHHH"
    __INODE_PACK__ = "<HHIIIIIHHII4s60sIIII12s"

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

    def _read_data(self, bg, inode):
        data = b''

        if inode.i_flags & 0x10000000:
            data = inode.i_block
        elif inode.i_flags & 0x80000:
            print("Inode uses extents")
            pass  # TODO read data by extents
        else:
            raise RuntimeError("Mapping Inodes not supported")

        return data

    def load(self, filename):
        self._ext4 = open(filename, "rb")
        self._ext4.seek(1024)
        self._superblock = self.__SuperBlock__._make(unpack(self.__SUPERBLOCK_PACK__, self._ext4.read(204)))
        if self._superblock.s_magic != 0xef53:
            raise RuntimeError("Bad superblock magic")
        self._block_size = 2 ** (10 + self._superblock.s_log_block_size)

    def readdir(self, inode_num):
        inode, bg = self._read_inode(inode_num)
        # noinspection PyTypeChecker
        dir_data = self._read_data(bg, inode)
        return dir_data  # TODO make list of dicts

    @property
    def root(self):
        return self.readdir(2)


class Application(object):
    def __init__(self):
        self._args = None

    def __parse_args(self):
        parser = argparse.ArgumentParser()

        parser.add_argument("-v", "--verbose", dest='verbose', help="verbose output",
                            action='store_true')
        parser.add_argument("-D", "--directory", dest='directory', type=str, help="set output directory", default=".")
        parser.add_argument("filename", type=str, help="EXT4 device or image")

        try:
            self._args = parser.parse_args()
        except SystemExit:
            sys.exit(2)

    def __do_extract(self):
        ext4 = Ext4(self._args.filename)
        print(ext4.root)

    def run(self):
        self.__parse_args()
        self.__do_extract()


if __name__ == '__main__':
    app = Application()
    app.run()
