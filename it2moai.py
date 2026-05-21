#!/usr/bin/env python3

"""
it2moai.py, version 0.3
----------------------

Python 3 only.

Use the example.it or .mptm file to do your song. When done, run this 
script and it will generate an output.moai file usable by 
thirtydollar.website.

Don't change the samples/instruments (.mptm instrument Alternative Tuning may be changed).
Only notes and volume settings are parsed. Commands are not parsed except for EFx/FFx/EEx/EFx in rows containing notes (for detuning)
Note Cuts ^ will cut all sounds, no matter where they are placed (i.e., be careful with these)

Initial settings:
Initial Tempo: adjustable
Ticks/Row: 3 (fixed, do not change)
Initial Global Vol: adjustable (template set at 60)
Sample Volume: 160 (this may be adjusted but does not affect the output, it is set so that tracker output during playback sounds closer to Moai website output)

Version history
---------------

* 0.1: Initial creation of program by kleeder
* 0.2: Added global volume initial setting, note volumes, and updated the soundlist to incorporate the 
       current available sounds (list grows from 131 samples to 191). Samples tuned in example module 
       and appropriate offsets added to the soundlist. Adjusted global/sample volume defaults so that
       tracker playback volume sounds closer to moai playback volume.
* 0.3: Module name is no longer hardcoded and must instead be typed in. Output name remains as is.
       Added ability to xenharmonise files during moai conversion to any tone equal temperament tuning
       system. This may be handy for .mptm files with such a tuning.
* 0.4: Support added for Fine/Extra Fine Portamento Down/Up commands (EFx/FFx/EEx/FEx) to detune notes.
       Use only on rows that also contain a note, otherwise the script will break.
* 0.5: Fixed errors on non-existent patterns and notes
"""

from argparse import ArgumentParser
from sys import stderr, version_info, argv
from pytrax import impulsetracker
import json
import math

def die(msg):
    print(msg, file=stderr)
    exit(1)


if version_info.major < 3:
    die('python3 only!')

def get_soundlist(soundlist_file):
    file = open(file=soundlist_file, encoding="utf8")
    soundlist = json.load(file)
    soundnamelist = []
    tuningoffsetlist = []
    # After populating instrument names, 
    # load the file again to get a list of tuning offsets. Samples were tuned to C in the tracker, and offset in the soundlist accordingly to keep them aligned with the tunings 
    # of the source files on thirtydollar.website.
    for x in soundlist:
        soundnamelist.append(x["name"])        
        tuningoffsetlist.append(x["tuningoffset"]) 
    return soundnamelist,tuningoffsetlist

def convert(module, filename, soundnamelist, tuninglist, edo = 12, origin_note = 0):
    outfile = open(filename, 'w', encoding="utf8")

    inittempo = (module["inittempo"])*8
    initvol = math.floor((module["globvol"])/128*100) # change global volume to a percentage
    sequence = module["orders"]

    outfile.write('!speed@{}|'.format(inittempo))
    outfile.write('!volume@{}|'.format(initvol))    

    for pattern_number in sequence:
        if pattern_number != 255:
            # Skip patterns that don't exist
            if len(module["patterns"]) < pattern_number or len(module["patterns"][pattern_number]) < 1:
                continue
            pattern_data = module["patterns"][pattern_number][0]
            for row in pattern_data:
                note_written = False
                for channel in row:
                    note = channel.get("note")
                    # Skip notes that don't exist
                    if not note:
                        continue
                    try:
                        cur_vol = math.floor(channel['volpan']/64*100) # change note volume setting to a floored percentage
                    except:
                        cur_vol = 100
                    if note == 254:
                        outfile.write('!cut|')
                    else:
                        if note_written:
                            outfile.write('!combine|')

                        instrument = channel["instrument"]
                        sample = soundnamelist[instrument-1] # write to the correct instrument as mapped in the soundlist
                        pitch = note-60+tuninglist[instrument-1] # adjust pitch with the offset from the soundlist
                        # if user wants regular tuning, this is skipped, otherwise, the notes are remapped to the new EDO
                        if (edo!=12.0):
                            ratio=12/edo
                            pitch=((pitch-origin_note)*ratio)+origin_note
                        # Checking for Fine/Extra Fine Portamento Down/Up commands (EFx, FFx, EEx, FEx)
                        # Applies a pitch offset (detune) to rows containing both a note and one of these commands
                        # Note that trying to use these commands in a row without a note will break the script
                        if ('command' in channel):
                            if ("EF" in channel["command"]) or ("FF" in channel["command"]) or ("EE" in channel["command"]) or ("FE" in channel["command"]):
                                cmd = channel["command"]
                                pitchoffset = int(cmd[2],16) * 0.0625
                                if (cmd[0]=='F'): pitchoffset = pitchoffset * -1
                                if (cmd[1]=='E'): pitchoffset = pitchoffset / 4
                                pitch = pitch - pitchoffset
                        # If the note is at default sample pitch offset of 0, don't bother writing pitch (for cleaner json)
                        # If the note volume is set to 100%, don't bother writing (for cleaner json + improved readability of volume settings in UI)
                        if (cur_vol==100):
                            if (pitch==0):
                                outfile.write(sample + '|')
                            else:
                                outfile.write(sample + '@' + str(pitch) + '|')
                        else:
                            if (pitch==0):
                                outfile.write(sample + "%" + str(cur_vol) + '|')
                            else:
                                outfile.write(sample + '@' + str(pitch) + "%" + str(cur_vol) + '|')
                        note_written = True

                if not note_written:
                    outfile.write('_pause|')

    outfile.close()

if __name__ == '__main__':
    output_path = None

    if len(argv) > 1:
        argparser = ArgumentParser()
        argparser.add_argument("input", help="input module (.it or .mptm supported)")
        argparser.add_argument("--output", help="output .🗿 file path, defaults to input filename with moai extension")
        argparser.add_argument("--edo", type=float, default=12, help="equal divisions of the octave, default is 12")
        argparser.add_argument("--origin-note", type=float, help="central semitone to remap all notes around, required if EDO is other than 12")

        args = argparser.parse_args()

        input_path  = args.input
        edo = args.edo
        origin_note = args.origin_note
        output_path = args.output
        if edo != 12 and not origin_note:
            die('origin note must be specified when EDO is not 12')
    else:
        try:
            input_path = input("Enter module name, .it or .mptm file format included: ")
            edo = float(input("Enter desired 'number of equal divisions of the octave': "))
            if edo!=12:
                origin_note = float(input("Enter central semitone to remap all the notes around: "))
        except BaseException as ex:
            die(ex)

    if not output_path:
        if input_path.casefold().endswith('.it'):
            output_path = input_path[:-3] + '.🗿'
        elif input_path.casefold().endswith('.mptm'):
            output_path = input_path[:-5] + '.🗿'
        else:
            output_path = input_path + '.🗿'

    module = impulsetracker.parse_file(input_path, with_patterns=True)
    soundnamelist,tuninglist = get_soundlist("soundlist.json")
    convert(module, output_path, soundnamelist, tuninglist, edo, origin_note)
    print(f"Output written to '{output_path}'", file=stderr)
