# Copyright (c) 2023-present The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit/.

file(READ ${RAW_SOURCE_PATH} hex_content HEX)
string(LENGTH "${hex_content}" hex_length)

get_filename_component(raw_source_basename ${RAW_SOURCE_PATH} NAME_WE)
file(WRITE ${HEADER_PATH}
  "#include <cstddef>\n"
  "#include <span>\n"
  "namespace ${RAW_NAMESPACE} {\n"
  "inline constexpr std::byte detail_${raw_source_basename}_raw[]{\n"
)

set(bytes_per_line 8)
math(EXPR hex_per_line "${bytes_per_line} * 2")
set(chunk_bytes 4096)
math(EXPR chunk_hex "${chunk_bytes} * 2")

set(offset 0)
while(offset LESS hex_length)
  math(EXPR remaining "${hex_length} - ${offset}")
  if(remaining GREATER_EQUAL chunk_hex)
    set(cur_chunk_size ${chunk_hex})
  else()
    set(cur_chunk_size ${remaining})
  endif()
  string(SUBSTRING "${hex_content}" ${offset} ${cur_chunk_size} chunk)
  string(REGEX REPLACE "([0-9a-f][0-9a-f])" "std::byte{0x\\1}," formatted "${chunk}")
  string(REGEX REPLACE "(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)(std::byte\\{0x[0-9a-f][0-9a-f]\\},)" "\\1\\2\\3\\4\\5\\6\\7\\8\n" formatted "${formatted}")
  file(APPEND ${HEADER_PATH} "${formatted}\n")
  math(EXPR offset "${offset} + ${cur_chunk_size}")
endwhile()

file(APPEND ${HEADER_PATH}
  "};\n"
  "inline constexpr std::span ${raw_source_basename}{detail_${raw_source_basename}_raw};\n"
  "}"
)
