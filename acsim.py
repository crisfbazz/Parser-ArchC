#!/usr/bin/env python

# -*- coding: utf-8 -*-
#**
# @file      acsim.c
# @author    Sandro Rigo
#
#            The ArchC Team
#            http://www.archc.org/
#
#            Computer Systems Laboratory (LSC)
#            IC-UNICAMP
#            http://www.lsc.ic.unicamp.br/
#
# @version   1.0
# @date      Mon, 19 Jun 2006 15:33:20 -0300
#
# @brief     The ArchC pre-processor.
#            This file contains functions to control the ArchC
#            to emit using templates the source files that compose
#            the behavioral simulator.
#
# @attention Copyright (C) 2002-2006 --- The ArchC Team
#
#**

import argparse
import string, re
import sys, os, os.path
from Cheetah.Template import Template
from acParser import acParser

def CreateFile(project_name, fileName, tmplName, dataList):
  try:
    #!Open file and write the template filled in it
    tmpl = Template(file = os.path.dirname(os.path.abspath(sys.argv[0])) + "/../etc/Templates/" + tmplName, searchList = [dataList])
    f = open(fileName, 'w')
    f.write(str(tmpl))
    f.close()
  except IOError:
    AC_ERROR("ArchC could not open output file " + fileName)
    exit(1)

def ReadConfFile():
  #!Open archc.conf file and gather the configure information from it
  try:
    confFile = os.path.dirname(os.path.abspath(sys.argv[0])) + "/../etc/archc.conf"
    f = open(confFile, 'r')
    lines = f.readlines()
    data = []
    dict_conf = {}
    for l in lines:
      if '=' in l:
        l = l.rstrip()
        data.append((l.split(' =')))
        #Change the name of the flags to the standard
        if data[-1][0] == "CC":
          data[-1][0] = "CC_PATH"
        elif data[-1][0] == "OPT":
          data[-1][0] = "OPT_FLAGS"
        elif data[-1][0] == "DEBUG":
          data[-1][0] = "DEBUG_FLAGS"
        elif data[-1][0] == "OTHER":
          data[-1][0] = "OTHER_FLAGS"
        #pass the values to a dictionary
        dict_conf[data[-1][0]] = data[-1][1]
    f.close()
    print "rola" + os.path.dirname(os.path.abspath(sys.argv[0]))
    dict_conf['BINDIR'] =  os.path.dirname(os.path.abspath(sys.argv[0]))
    dict_conf['INCLUDEDIR'] = os.path.dirname(os.path.abspath(sys.argv[0])) + "/../include/archc"
    dict_conf['LIBDIR'] = os.path.dirname(os.path.abspath(sys.argv[0])) + "/../lib"
    if not dict_conf['SYSTEMC_PATH']:
      AC_ERROR("Please configure a SystemC path running install.sh script in ArchC directory.")
      exit(1)

    return dict_conf
  except IOError:
    AC_ERROR("Could not open archc.conf configuration file.")
    exit(1)

def invert_fields(formats):
  for key in formats.keys():
    if type(formats[key]) == list:
      formats[key].reverse()

  return formats

def ShowDecodeList(ac_dec_list):
  for dec in ac_dec_list:
    print "ac_dec_list"
    print "    Name : " + dec['name']
    print "    ID : " + str(dec['id'])
    print "    Value: " + str(dec['value'])

def ShowDecInstr(instr_list):
  for instr in instr_list:
    print "ac_dec_instr"
    print "Name    : " + instr['name']
    print "Mnemonic: " + instr['mnemonic']
    print "ASM     : " + str(instr['asm_str'])
    print "Format  : " + instr['format']
    print "Decode List: "
    ShowDecodeList(instr['dec_list'])

def ShowDecFormat(ac_dec_format):
  for dec in ac_dec_format:
    print "ac_dec_format"
    print "Name: " + dec['name']
    print "Fields:"
    ShowDecField(dec['fields'])

def ShowDecField(ac_dec_field):
  for dec in ac_dec_field:
    print "ac_dec_field"
    print "    Name : " + dec['name']
    print "    Size : " + str(dec['size'])
    print "    First: " + str(dec['first_bit'])
    print "    ID   : " + str(dec['id'])

def ShowDecoder(dec):
  ident = "    "
  for decoder in dec:
    id = 0
    for field in decoder['fields']:
      print ident*id + "ac_decoder: "
      print "" + ident*id + " Field: "
      print "" + ident*id + "  Name: " + field['name'] + ""
      print "" + ident*id + "  Val : " + str(field['value'])
      id += 1
    id -= 1
    print ident*id + "Instruction Found:"
    print "" + ident*id + "  Name    : " + decoder['instruction']['name'] + ""
    print "" + ident*id + "  Mnemonic: " + decoder['instruction']['mnemonic']

def AC_MSG(msg):
  #! Issuing an  message *#
  print "ArchC: " + msg

def AC_ERROR(msg):
  #*! Issuing an Error message *#
  print "ArchC ERROR: " + msg

## Command-line options flags
ACABIFlag=0                 #!<Indicates whether an ABI was provided or not
ACDebugFlag=0               #!<Indicates whether debugger option is turned on or not
ACDecCacheFlag=1            #!<Indicates whether the simulator will cache decoded instructions or not
ACDelayFlag=0               #!<Indicates whether delay option is turned on or not
ACDDecoderFlag=0            #!<Indicates whether decoder structures are dumped or not
ACStatsFlag=0               #!<Indicates whether statistics collection is enable or not
ACVerboseFlag=0             #!<Indicates whether verbose option is turned on or not
ACGDBIntegrationFlag=0      #!<Indicates whether gdb support will be included in the simulator
ACWaitFlag=1                #!<Indicates whether the instruction execution thread issues a wait() call or not
ACThreading=1               #!<Indicates if Direct Threading Code is turned on or not
ACSyscallJump=1             #!<Indicates if Syscall Jump Optimization is turned on or not
ACForcedInline=1            #!<Indicates if Forced Inline in Interpretation Routines is turned on or not
ACLongJmpStop=1             #!<Indicates if New Stop using longjmp is turned on or not
ACIndexFix=0                #!<Indicates if Index Decode Cache Fix Optimization is turned on or not
ACPCAddress=1               #!<Indicates if PC bounds is verified or not
ACFullDecode=0              #!<Indicates if Full Decode Optimization is turned on or not
ACCurInstrID=1              #!<Indicates if Current Instruction ID is save in dispatch

ACVERSION = "2.2"

#* Handling command line options *#
args_parser = argparse.ArgumentParser(description = "========================================================================== This is the ArchC Simulator Generator version " + ACVERSION + " ==========================================================================",
                                      epilog = "For more information please visit www.archc.org")
#!Define the table of mappings. Manage command line options.
args_parser.add_argument("model", type = str, help = "The AC_ARCH description file.")

args_parser.add_argument( "--abi-included"   , "-abi", dest = "OPABI"           , help = "Indicate that an ABI for system call emulation was provided."   , action = 'store_true')
args_parser.add_argument( "--debug"          , "-g"  , dest = "OPDebug"         , help = "Enable simulation debug features: traces, update logs."         , action = 'store_true')
args_parser.add_argument( "--delay"          , "-dy" , dest = "OPDelay"         , help = "Enable delayed assignments to storage elements."                , action = 'store_true')
args_parser.add_argument( "--dumpdecoder"    , "-dd" , dest = "OPDDecoder"      , help = "Dump the decoder data structure."                               , action = 'store_true')
args_parser.add_argument("--no-dec-cache"    , "-ndc", dest = "OPDecCache"      , help = "Disable cache of decoded instructions."                         , action = 'store_true')
args_parser.add_argument("--stats"           , "-s"  , dest = "OPStats"         , help = "Enable statistics collection during simulation."                , action = 'store_true')
args_parser.add_argument("--verbose"         , "-vb" , dest = "OPVerbose"       , help = "Display update logs for storage devices during simulation."     , action = 'store_true')
args_parser.add_argument("--version"         , "-vrs", dest = "OPVersion"       , help = "Display ACSIM version."                                         , action = 'version', version = "This is ArchC version " + ACVERSION)
args_parser.add_argument("--gdb-integration" , "-gdb", dest = "OPGDBIntegration", help = "Enable support for debbuging programs running on the simulator.", action = 'store_true')
args_parser.add_argument("--no-wait"         , "-nw" , dest = "OPWait"          , help = "Disable wait() at execution thread."                            , action = 'store_true')
args_parser.add_argument("--no-threading"    , "-nt" , dest = "OPDTC"           , help = "Disable Direct Threading Code."                                 , action = 'store_true')
args_parser.add_argument("--no-syscall-jump" , "-nsj", dest = "OPSysJump"       , help = "Disable Syscall Jump Optimization."                             , action = 'store_true')
args_parser.add_argument("--no-forced-inline", "-nfi", dest = "OPForcedInline"  , help = "Disable Forced Inline in Interpretation Routines."              , action = 'store_true')
args_parser.add_argument("--no-new-stop"     , "-nns", dest = "OPLongJmpStop"   , help = "Disable New Stop Optimization."                                 , action = 'store_true')
args_parser.add_argument("--index-fix"       , "-idx", dest = "OPIndexFix"      , help = "Enable Index Decode Cache Fix Optimization."                    , action = 'store_true')
args_parser.add_argument("--no-pc-addr-ver"  , "-npv", dest = "OPPCAddress"     , help = "Disable PC address verification."                               , action = 'store_true')
args_parser.add_argument("--full-decode"     , "-fdc", dest = "OPFullDecode"    , help = "Enable Full Decode Optimization."                               , action = 'store_true')
args_parser.add_argument("--no-curr-instr-id", "-nci", dest = "OPCurInstrID"    , help = "Disable Current Instruction ID save in dispatch."               , action = 'store_true')
#Process the command line
args = args_parser.parse_args()

#!Teste if the input file is valid.
try:
  arch_filename = args.model
  file_teste = open(arch_filename)
  file_teste.close()
except IOError:
  AC_ERROR("Invalid input file: " + arch_filename + '\n' + "   Try python acsim.py --help for more information.")
  exit(1)

#* Searching option map.*#
ACOptions = []
if args.OPABI:
  ACABIFlag = 1
  ACOptions.append("-abi")
if args.OPDebug:
  ACDebugFlag = 1
  ACOptions.append("-g")
if args.OPDelay:
  ACDelayFlag = 1
  ACOptions.append("-dy")
if args.OPDDecoder:
  ACDDecoderFlag = 1
  ACOptions.append("-dd")
if args.OPDecCache:
  ACDecCacheFlag = 0
  ACOptions.append("-ndc")
if args.OPStats:
  ACStatsFlag = 1
  ACOptions.append("-s")
if args.OPVerbose:
  ACVerboseFlag = 1
  ACOptions.append("-vb")
  AC_MSG("Simulator running on verbose mode.")
if args.OPGDBIntegration:
  ACGDBIntegrationFlag = 1
  ACOptions.append("-gdb")
if args.OPWait:
  ACWaitFlag = 0
  ACOptions.append("-nw")
if args.OPDTC:
  ACThreading = 0
  ACOptions.append("-nt")
if args.OPSysJump:
  ACSyscallJump = 0
  ACOptions.append("-nsj")
if args.OPForcedInline:
  ACForcedInline = 0
  ACOptions.append("-nfi")
if args.OPLongJmpStop:
  ACLongJmpStop = 0
  ACOptions.append("-nns")
if args.OPIndexFix:
  ACIndexFix = 1
  ACOptions.append("-idx")
if args.OPPCAddress:
  ACPCAddress = 0
  ACOptions.append("-npv")
if args.OPFullDecode:
  ACFullDecode = 1
  ACOptions.append("-fdc")
if args.OPCurInstrID:
  ACCurInstrID = 0
  ACOptions.append("-nci")

if not ACDecCacheFlag:
  ACFullDecode = 0

#Loading Configuration Variables
data_conf = ReadConfFile()

#*Parsing Architecture declaration file. *#
parser = acParser()
parser.ParseFile(arch_filename)
parser_info = parser.GetInfo()

# Getting the architecture name and file name
project_name = parser_info.fileName
upper_project_name = project_name.upper()
isa_filename = parser_info.info['ac_isa']

# Here we get all the other tokens from the parser_info.code
if 'ac_wordsize' in parser_info.info:
  wordsize = parser_info.info['ac_wordsize']
else:
  AC_MSG("Warning: No wordsize defined. Default value is 32 bits.")
  wordsize = 32

if 'ac_fetchsize' in parser_info.info:
  fetchsize = parser_info.info['ac_fetchsize']
else:
  AC_MSG("Warning: No fetchsize defined. Default is to be equal to wordsize (" + str(wordsize) + ").")
  fetchsize = wordsize

##Testing host endianess.
#Analyzes if the endian of the simulated arch is big endian
ac_tgt_endian = int(parser_info.info['set_endian'] == "big")
#Analyzes if the endian of the host machine is big endian
ac_host_endian = int(sys.byteorder == "big")
#Analyzes if the simulated arch match the endian with host
ac_match_endian = int(parser_info.info['set_endian'] == sys.byteorder)

#If target is little endian, invert the order of fields in each format.
#This is the way the little endian decoder expects format fields.
if ac_tgt_endian == 0:
  parser_info.info['ac_format'] = invert_fields(parser_info.info['ac_format'])

ac_storage_list = []  ##!< A list of dictionaries with all the storage types
if 'ac_cache_parms' in parser_info.info:
  HaveMemHier = 1
  c_parms = parser_info.info['ac_cache_parms']
  cache_parms = []
  for parm in c_parms:
    # Extract the number from the string
    p_value = re.findall(r'\d+', parm)
    # Check if there was a number in the string and get the rest of the string as a text
    if p_value:
      p_value = p_value[0]
      p_str = parm.replace(p_value,"")
    else:
      p_value = 0
      p_str = parm
    cache_parms.append({'str': p_str, 'value': int(p_value)})
else:
  cache_parms = 0
  HaveMemHier = 0

if 'ac_cache' in parser_info.info:
  tmp = parser_info.info['ac_cache']
  cache = {}
  for i in tmp.keys():
    cache[i] = tmp[i]
    ac_storage_list.append({'type': "CACHE", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': cache_parms})
else:
  cache = None

if 'ac_icache' in parser_info.info:
  tmp = parser_info.info['ac_icache']
  icache = {}
  for i in tmp.keys():
    icache[i]= tmp[i]
    ac_storage_list.append({'type': "ICACHE", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': cache_parms})
  fetch_device = {'type': "ICACHE", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': cache_parms}
else:
  icache = None
  fetch_device = None

if 'ac_dcache' in parser_info.info:
  tmp = parser_info.info['ac_dcache']
  dcache = {}
  for i in tmp.keys():
    dcache[i] = tmp[i]
    ac_storage_list.append({'type': "DCACHE", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': cache_parms})
else:
  dcache = None

if 'ac_mem' in parser_info.info:
  tmp = parser_info.info['ac_mem']
  mem = {}
  for i in tmp.keys():
    mem[i] = tmp[i]
    ac_storage_list.append({'type': "MEM", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': 0})
else:
  mem = 0

if 'ac_regbank' in parser_info.info:
  tmp = parser_info.info['ac_regbank']
  regbank = {}
  for i in tmp.keys():
    regbank[i] = tmp[i]
    if tmp[i][1] == None:
      width = 0
    else:
      width = tmp[i][1]
    if tmp[i][0] == None:
      size = 0
    else:
      size = tmp[i][0]
    ac_storage_list.append({'type': "REGBANK", 'name': i, 'width': width, 'size': size, 'format': None, 'level': 0, 'higher': 0, 'parms': 0})
else:
  regbank = None

if 'ac_reg' in parser_info.info:
  tmp = parser_info.info['ac_reg']
  reg = {}
  for i in tmp.keys():
    if tmp[i] == None:
      parms = 0
      p_value = 0
    else:
      # Extract the number from the string
      p_value = re.findall(r'\d+', str(tmp[i]))
      # Check if there was a number in the string and get the rest of the string as a text
      if p_value:
        p_value = p_value[0]
        p_str = str(tmp[i]).replace(p_value,"")
      else:
        p_value = 0
        p_str = tmp[i]
      parms = {'str': p_str, 'value': int(p_value)}

    reg[i] = tmp[i]
    ac_storage_list.append({'type': "REG", 'name': i, 'width': int(p_value), 'size': 0, 'format': None, 'level': 0, 'higher': 0, 'parms': parms})
  HaveFormattedRegs = 0
else:
  reg = None
  HaveFormattedRegs = 0

if 'bindTo' in parser_info.info:
  tmp = parser_info.info['bindTo']
  bind = {}
  for i in tmp.keys():
    bind[i] = tmp[i]
else:
  bind = None

if 'pseudo_instr' in parser_info.info:
  tmp = parser_info.info['pseudo_instr']
  pseudo = {}
  for i in tmp.keys():
    pseudo[i] = tmp[i]
else:
  pseudo = []

if 'ac_tlm_port' in parser_info.info:
  tmp = parser_info.info['ac_tlm_port']
  tlm_ports = []
  cur_id = 1 ##!< Used to attribute sequential IDs
  for i in tmp.keys():
    tlm_ports.append({'name': i, 'id': cur_id})
    cur_id += 1
    ac_storage_list.append({'type': "TLM_PORT", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': 0})
  HaveTLMPorts = 1
else:
  tlm_ports = []
  HaveTLMPorts = 0

if 'ac_tlm2_port' in parser_info.info:
  tmp = parser_info.info['ac_tlm_port']
  tlm2_ports = []
  cur_id = 1 ##!< Used to attribute sequential IDs
  for i in tmp.keys():
    tlm2_ports.append({'name': i, 'id': cur_id})
    cur_id += 1
    ac_storage_list.append({'type': "TLM2_PORT", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': 0})
  HaveTLM2Ports = 1
else:
  tlm2_ports = []
  HaveTLM2Ports = 0

if 'ac_tlm2_nb_port' in parser_info.info:
  tmp = parser_info.info['ac_tlm_port']
  tlm2_nb_ports = []
  cur_id = 1 ##!< Used to attribute sequential IDs
  for i in tmp.keys():
    tlm2_nb_ports.append({'name': i, 'id': cur_id})
    cur_id += 1
    ac_storage_list.append({'type': "TLM2_NB_PORT", 'name': i, 'width': 0, 'size': tmp[i], 'format': None, 'level': 0, 'higher': 0, 'parms': 0})
  HaveTLM2NBPorts = 1
else:
  tlm2_nb_ports = []
  HaveTLM2NBPorts = 0

if 'ac_tlm_intr_port' in parser_info.info:
  tmp = parser_info.info['ac_tlm_intr_port']
  tlm_intr_ports = []
  cur_id = 1 ##!< Used to attribute sequential IDs
  for i in tmp.keys():
    tlm_intr_ports.append({'name': i, 'id': cur_id})
    cur_id += 1
  HaveTLMIntrPorts = 1
else:
  tlm_intr_ports = []
  HaveTLMIntrPorts = 0

if 'ac_tlm2_intr_port' in parser_info.info:
  tmp = parser_info.info['ac_tlm2_intr_port']
  tlm2_intr_ports = []
  cur_id = 1 ##!< Used to attribute sequential IDs
  for i in tmp.keys():
    tlm2_intr_ports.append({'name': i, 'id': cur_id})
    cur_id += 1
  HaveTLM2IntrPorts = 1
else:
  tlm2_intr_ports = []
  HaveTLM2IntrPorts = 0


format_ins_list = []     ##!< A list of dictionaries with all the instructions
formats_fields = []      ##!< Have all the fields of all the formats
decoder_nFields = 0      ##!< Stores the total number of fields in all formats
largest_format_size = 0  ##!< Stores the number of fields of the format with more fields
n_const = 0              ##!< Used to attribute sequential Constant numbers to all fields that have a Constant as a name
if 'ac_format' in parser_info.info:
  tmp = parser_info.info['ac_format']
  instr_id = 0
  for i in tmp:
    cur_id = 1  ##!< Used to attribute sequential IDs to the commons list
    instr_id += 1
    format = {'name':i,'fields':[], 'id': instr_id, 'size': wordsize}
    tmp_value = 0
    ##if is just one tuple, analyzes it separately
    if type(tmp[i]) != list:
      decoder_nFields += 1
      name = tmp[i][0]
      value = int(tmp[i][1])
      first = value - 1
      if type(name) == int:
        name = "CONST_" + str(n_const)
        n_const += 1
      if tmp[i].__len__() > 2:
        sign = 1
      else:
        sign = 0
      format['fields'].append({'name': name,'id': cur_id,'sign': sign, 'size': value, 'first_bit': first, 'val': 0})
      format_ins_list.append(format)
      formats_fields.append({'name': name, 'sign': sign, 'size': value, 'val': 0})
      continue
    else:
      decoder_nFields += tmp[i].__len__()
    ##analyses all the tuples field in the list
    for j in tmp[i]:
      name = j[0]
      value = int(j[1])
      if cur_id == 1:
        first = value - 1
      else:
        first = first + value
      ##if the name is a constant, change it to the standard
      if type(name) == int:
        name = "CONST_" + str(n_const)
        n_const += 1
        ##if has the third element "s" in the field, sign it
      if j.__len__() > 2:
        sign = 1
      else:
        sign = 0
      format['fields'].append({'name': name,'id': cur_id, 'sign': sign, 'size': value, 'first_bit': first, 'val': 0})
      formats_fields.append({'name': name, 'sign': sign, 'size': value, 'val': 0})
      ##sum the value of the field to find the largest one
      tmp_value += (int(''.join(map(str,j[1]))))  #transform string in integer
      cur_id += 1
    if (tmp_value > largest_format_size and not(tmp_value%2)):  #if is not even, then discard (cases with or in the type format)
      largest_format_size = tmp_value
    format_ins_list.append(format)
else:
  largest_format_size = 0
  decoder_nFields = 0

format_num = parser_info.info['ac_format'].__len__()
decoder_nFields = decoder_nFields + 1

common_instr_field_list = []
##process common_instr_field_list, a list with the fields that are common to all formats of instructions
if format_num > 1:
  for i in formats_fields:
    field_count = formats_fields.count(i) ##get the number of times that a field appear in all the formats
    if type(i['name']) != int:  ##each constant is different from each other, discard all
      if field_count >= format_num:
        ##if the field appear in all formats, save it and then discard it from the possibilities(formats_fields)
        common_instr_field_list.append(i)
        formats_fields.remove(i)
      else:
        ##if the field don't appear in all formats just discart it
        formats_fields.remove(i)
    else:
      formats_fields.remove(i)
else:
  common_instr_field_list = formats_fields

if 'ac_helper' in parser_info.info:
  tmp = parser_info.info['ac_helper']
  helper = tmp
else :
  helper = None

if 'ac_asm_map' in parser_info.info:
  tmp = parser_info.info['ac_asm_map']
  asmmap = []
  for i in tmp.keys():
    asmmap.append({'name':i, 'maps': tmp[i]})
else:
  asmmap = []

# default values
HaveCycleRange = 0
HaveMultiCycleIns = 0

decoder = []
instr_list = []
asms = []
delays = []
group = []
declist_num = 0
instr_num = 0
for i in parser_info.instructions:
  commands = parser_info.info[i]
  instr_num += 1
  instr = {'name': i, 'mnemonic': i,'format': parser_info.instructions[i], 'id': instr_num, 'cycles': 1, 'size': wordsize/8, 'delay': 0, 'asm_str': None, 'dec_list': None, 'min_latency': 1, 'max_latency': 1}

  if 'set_asm' in commands:
    tmp = commands['set_asm']
    asm = []
    for am in tmp:
      asm.append(am)
    asms.append(asm)
    # if there is more then one set_asm, take the first
    while type(asm[0]) == list:
      asm[0] = asm [0][0]
    instr['asm_str'] = asm[0]
    instr['mnemonic'] = str(asm[0]).split("%reg")[0]

  if 'set_decoder' in commands:
    declist_num += commands['set_decoder'].__len__()
    decoder_fields = []
    for tmp in commands['set_decoder']:
      decoder_fields.append({'name': tmp[0], 'value': tmp[1], 'id': (commands['set_decoder'].index(tmp) + 1)})
    decoder.append({'fields': decoder_fields, 'instruction': {'name': instr['name'], 'mnemonic': instr['mnemonic']} })
    instr['dec_list'] = decoder_fields
  else:
    decoder = None
    declist_num = 0

  if 'set_cycles' in commands:
    instr['cycles'] = int(commands['set_cycles'])
    HaveMultiCycleIns = 1

  if 'cycle_range'in commands:
    instr['cycles'] = commands['cycle_range']
    HaveCycleRange = 1

  if 'delay' in commands:
    instr['delay'] = int(commands['delay'][0])
    delays.append({'name': i, 'delay': int(commands['delay'][0])})

  if 'cond' in commands:
    conds = commands['cond']
  else:
    conds = None

  if 'delay_cond' in commands:
    delay_conds = commands['delay_cond']
  else:
    delay_conds = None

  if 'behavior' in commands:
    behaviors = commands['behavior']
  else:
    behaviors = None

  if 'is_jump' in commands:
    isjumps = commands['is_jump']
  else:
    isjumps = None

  if 'is_branch' in commands:
    isbranchs = commands['is_branch']
  else:
    isbranchs = None

  if 'ac_group' in commands:
    tmp = commands['ac_group']
    ins_list = []
    flag_allocate = 0
    for item in group:
      if item["name"] == i and item["element"] == tmp[i]:
        item["instrs"].append(instr)
        flag_allocate = 1
        break
    if not flag_allocate:
      instr_list.append(instr)
      group.append({'name': i, 'element': tmp[i], 'instrs': ins_list})
  else:
    group = []

  instr_list.append(instr)

instr_num = parser_info.instructions.__len__()

if 'ac_mem' in parser_info.info:
  load_device = {'size': parser_info.info['ac_mem'].values()[0], 'name': parser_info.info['ac_mem'].keys()[0], 'level': 0, 'higher': 0}
elif 'ac_icache' in parser_info.info:
  load_device = {'size': parser_info.info['ac_icache'].values()[0], 'name': parser_info.info['ac_icache'].keys()[0], 'level': 0, 'higher': 0}
elif 'ac_cache' in parser_info.info:
  load_device = {'size': parser_info.info['ac_cache'].values()[0], 'name': parser_info.info['ac_cache'].keys()[0], 'level': 0, 'higher': 0}
elif 'ac_dcache' in parser_info.info:
  load_device = {'size': parser_info.info['ac_dcache'].values()[0], 'name': parser_info.info['ac_dcache'].keys()[0], 'level': 0, 'higher': 0}
else:
  load_device = {'size': 0, 'name': "nothing", 'level': 0}

##A Dictionary containing all the tokens needed to generate the templates
data_tmpl = {}
data_tmpl['ACABIFlag'] = ACABIFlag
data_tmpl['ACDebugFlag'] = ACDebugFlag
data_tmpl['ACDecCacheFlag'] = ACDecCacheFlag
data_tmpl['ACDelayFlag'] = ACDelayFlag
data_tmpl['ACDDecoderFlag'] = ACDDecoderFlag
data_tmpl['ACStatsFlag'] = ACStatsFlag
data_tmpl['ACVerboseFlag'] = ACVerboseFlag
data_tmpl['ACGDBIntegrationFlag'] = ACGDBIntegrationFlag
data_tmpl['ACWaitFlag'] = ACWaitFlag
data_tmpl['ACThreading'] = ACThreading
data_tmpl['ACSyscallJump'] = ACSyscallJump
data_tmpl['ACForcedInline'] = ACForcedInline
data_tmpl['ACLongJmpStop'] = ACLongJmpStop
data_tmpl['ACIndexFix'] = ACIndexFix
data_tmpl['ACPCAddress'] = ACPCAddress
data_tmpl['ACIndexFix'] = ACIndexFix
data_tmpl['ACFullDecode'] = ACFullDecode
data_tmpl['ACCurInstrID'] = ACCurInstrID
data_tmpl['ACOptions'] = ACOptions

data_tmpl['ACVERSION'] = ACVERSION

data_tmpl['arch_filename'] = arch_filename
data_tmpl['project_name'] = project_name
data_tmpl['upper_project_name'] = upper_project_name
data_tmpl['isa_filename'] = isa_filename

data_tmpl['wordsize'] = wordsize
data_tmpl['fetchsize'] = fetchsize

data_tmpl['ac_tgt_endian'] = ac_tgt_endian
data_tmpl['ac_host_endian'] = ac_host_endian
data_tmpl['ac_match_endian'] = ac_match_endian

data_tmpl.update(data_conf)

data_tmpl['CACHE'] = cache
data_tmpl['ICACHE'] = icache
data_tmpl['fetch_device'] = fetch_device
data_tmpl['DCACHE'] = dcache
data_tmpl['REG'] = reg
data_tmpl['REGBANK'] = regbank
data_tmpl['HaveFormattedRegs'] = HaveFormattedRegs
data_tmpl['MEM'] = mem

data_tmpl['HaveMemHier'] = HaveMemHier
data_tmpl['HaveCycleRange'] = HaveCycleRange
data_tmpl['HaveMultiCycleIns'] = HaveMultiCycleIns


data_tmpl['binds'] = bind
data_tmpl['pseudolist'] = pseudo

data_tmpl['tlm_port_list'] = tlm_ports
data_tmpl['HaveTLMPorts'] = HaveTLMPorts
data_tmpl['tlm2_port_list'] = tlm2_ports
data_tmpl['HaveTLM2Ports'] = HaveTLM2Ports
data_tmpl['tlm2_nb_port_list'] = tlm2_nb_ports
data_tmpl['HaveTLM2NBPorts'] = HaveTLM2NBPorts
data_tmpl['tlm_intr_port_list'] = tlm_intr_ports
data_tmpl['HaveTLMIntrPorts'] = HaveTLMIntrPorts
data_tmpl['tlm2_intr_port_list'] = tlm2_intr_ports
data_tmpl['HaveTLM2IntrPorts'] = HaveTLM2IntrPorts

data_tmpl['storage_list'] = ac_storage_list

data_tmpl['format_num'] = format_num
data_tmpl['largest_format_size'] = largest_format_size
data_tmpl['decoder_nFields'] = decoder_nFields
data_tmpl['format_ins_list'] = format_ins_list
data_tmpl['common_instr_field_list'] = common_instr_field_list

data_tmpl['helper_contents'] = helper

data_tmpl['group_list'] = group
data_tmpl['asmmap_list'] = asmmap
data_tmpl['conds'] = conds
data_tmpl['delay_conds'] = delay_conds
data_tmpl['behaviors'] = behaviors
data_tmpl['isjumps'] = isjumps
data_tmpl['isbranchs'] = isbranchs

data_tmpl['instr_num'] = instr_num
data_tmpl['instr_list'] = instr_list
data_tmpl['decoder_list'] = decoder
data_tmpl['asm_list'] = asms
data_tmpl['delay_list'] = delays

data_tmpl['load_device'] = load_device
data_tmpl['declist_num'] = declist_num

if ACDDecoderFlag:
  AC_MSG("Dumping decoder structures:")
  ShowDecInstr(instr_list)
  ShowDecFormat(format_ins_list)
  print '\n' + '\n'
  ShowDecoder(decoder)

#Creating Resources Header File
##! Create ArchC Resources Header File
## CreateArchHeader
CreateFile(project_name, (project_name+ "_arch.H"), ("project_name_arch_H.tmpl"), data_tmpl)
##*!Create ArchC Resources Reference Header File *
## CreateArchRefHeader
CreateFile(project_name, (project_name + "_arch_ref.H"), ("project_name_arch_ref_H.tmpl"), data_tmpl)

#Creating Resources Impl File
##*!Creates the _arch.cpp Implementation File. *
## CreateArchImpl
CreateFile(project_name, (project_name + "_arch.cpp"), ("project_name_arch_cpp.tmpl"), data_tmpl)
##*!Create ArchC Resources Reference Implementation File *
## CreateArchRefImpl
CreateFile(project_name, (project_name + "_arch_ref.cpp"), ("project_name_arch_ref_cpp.tmpl"), data_tmpl)

#Creating ISA Header File
##!Creates the ISA Header File.
## CreateISAHeader
CreateFile(project_name, (project_name + "_isa.H"), ("project_name_isa_H.tmpl"), data_tmpl)
##! opens behavior macros file
## Behavior Macros File.
CreateFile(project_name, (project_name + "_bhv_macros.H"), ("project_name_bhv_macros_H.tmpl"), data_tmpl)

##Don't declare stages anymore, even if a pipeline was declared
if 'ac_stage' in parser_info.info:
  AC_MSG("Warning: stage_list is no more used by acsim.")
if 'ac_pipe' in parser_info.info:
  AC_MSG("Warning: pipe_list is no more used by acsim.")

#Creating Processor Files
#!Creates Processor Module Header File
## CreateProcessorHeader
CreateFile(project_name, (project_name + ".H"), ("project_name_H.tmpl"), data_tmpl)
##!Creates Processor Module Implementation File
## CreateProcessorImpl
CreateFile(project_name, (project_name + ".cpp"), ("project_name_cpp.tmpl"), data_tmpl)

#Creating Formatted Registers Header and Implementation Files.
if HaveFormattedRegs:
  ##CreateRegsHeader
  if any((pstorage['type'] == 'REG' and pstorage['format'] != None) for pstorage in ac_storage_list):
    #!Creates Formatted Registers Header File
    CreateFile(project_name, (project_name + "_fmt_regs.H"), ("project_name_fmt_regs_H.tmpl"), data_tmpl)

if HaveTLMIntrPorts:
  #!Creates the header file for interrupt handlers.
  ## CreateIntrHeader
  CreateFile(project_name, (project_name + "_intr_handlers.H"), ("project_name_intr_handlers_H.tmpl"), data_tmpl)
  #!Creates the header file with ac_behavior macros for interrupt handlers.
  ## CreateIntrMacrosHeader
  CreateFile(project_name, (project_name + "_ih_bhv_macros.H"), ("project_name_ih_bhv_macros_H.tmpl"), data_tmpl)
  #!Creates the .cpp template file for interrupt handlers.
  ## CreateIntrTmpl
  CreateFile(project_name, (project_name+ "_intr_handlers.cpp.tmpl"), ("project_name_intr_handlers_cpp_tmpl.tmpl"), data_tmpl)

if HaveTLM2IntrPorts:
  #!Creates the header file for interrupt handlers.
  ## CreateIntrTLM2Header
  CreateFile(project_name, (project_name+ "_intr_handlers.H"), ("project_name_intr2_handlers_H.tmpl"), data_tmpl)
  #!Creates the header file with ac_behavior macros for interrupt handlers.
  ## CreateIntrTLM2MacrosHeader
  CreateFile(project_name, (project_name + "_ih_bhv_macros.H"), ("project_name_ih2_bhv_macros_H.tmpl"), data_tmpl)
  #!Creates the .cpp template file for interrupt handlers.
  ## CreateIntrTLM2Tmpl
  CreateFile(project_name, (project_name + "_intr_handlers.cpp.tmpl"), ("project_name_intr2_handlers_cpp_tmpl.tmpl"), data_tmpl)

#Creating Simulation Statistics class header file.
if ACStatsFlag:
  ##!Create the header file for ArchC statistics collection class.
  ## CreateStatsHeaderTmpl
  CreateFile(project_name, (project_name + "_stats.H.tmpl"), ("project_name_stats_H_tmpl.tmpl"), data_tmpl)
  ## CreateStatsImplTmpl
  CreateFile(project_name, (project_name + "_stats.cpp.tmpl"), ("project_name_stats_cpp_tmpl.tmpl"), data_tmpl)

#Creating model syscall header file.
if ACABIFlag:
  ##!Create ArchC model syscalls
  ## CreateArchSyscallHeader
  CreateFile(project_name, (project_name + "_syscall.H.tmpl"), ("project_name_syscall_H_tmpl.tmpl"), data_tmpl)

#Create the template for the .cpp instruction and format behavior file */
## CreateImplTmpl
CreateFile(project_name, (project_name + "_isa.cpp.tmpl"), ("project_name_isa_cpp_tmpl.tmpl"), data_tmpl)
## ac_isa_init creation starts here
# Name for ISA initialization file.
CreateFile(project_name, (project_name + "_isa_init.cpp"), ("project_name_isa_init_cpp.tmpl"), data_tmpl)

#Creating Parameters Header File
##!Creates Decoder Header File
## CreateParmHeader
CreateFile(project_name, (project_name + "_parms.H"), ("project_name_parms_H.tmpl"), data_tmpl)

#Create the template for the main.cpp  file
##!Create the template for the .cpp file where the user has the basic code for the main function.
## CreateMainTmpl
CreateFile(project_name, ("main.cpp.tmpl"), ("main_cpp_tmpl.tmpl"), data_tmpl)

#Create the Makefile
## CreateMakefile
CreateFile(project_name, ("Makefile.archc"), ("Makefile_archc.tmpl"), data_tmpl)

#Issuing final messages to the user.
AC_MSG(project_name + " model files generated.")







