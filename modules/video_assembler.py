import importlib
_mod = importlib.import_module("modules.4_video_assembler")
assemble_curated_video = _mod.assemble_curated_video
prepare_trimmed_segment = _mod.prepare_trimmed_segment
get_video_duration = _mod.get_video_duration
