"""Standalone Sony IMX500 camera and inference-pipeline benchmark.

This script intentionally has no MAVLink, ArduPilot or flight-control code.
It measures the observed camera-to-output processing cycle, not the latency of
the IMX500 accelerator chip in isolation.
"""

import argparse
import csv
import os
import platform
import statistics
import time

from picamera2 import Picamera2
from picamera2.devices import IMX500


def percentile(values, fraction):
    """Return a nearest-rank percentile from already collected samples."""
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def write_csv(path, samples):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame", "pipeline_cycle_ms", "detections"])
        writer.writerows(samples)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Sony IMX500 camera and inference pipeline."
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Path to the IMX500 .rpk model on the Raspberry Pi.",
    )
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional CSV output path for individual frame timings.",
    )
    args = parser.parse_args()

    if args.frames <= 0 or args.warmup < 0 or args.fps <= 0:
        parser.error("frames and fps must be positive; warmup cannot be negative")

    if not os.path.isfile(args.model):
        parser.error(f"Model was not found: {args.model}")

    print("=== IMX500 EDGE BENCHMARK ===")
    print(f"Host: {platform.node()}")
    print(f"Platform: {platform.platform()}")
    print(f"CPU cores reported: {os.cpu_count()}")
    print(f"Model: {args.model}")
    print(f"Model size: {os.path.getsize(args.model) / 1024 / 1024:.2f} MiB")
    print(f"Camera configuration: {args.width}x{args.height} at {args.fps} FPS")
    print(f"Warm-up frames: {args.warmup}; measured frames: {args.frames}")
    print("MAVLink and flight control are not used by this script.")

    imx500 = IMX500(args.model)
    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"},
        controls={"FrameRate": args.fps},
    )

    samples_ms = []
    csv_rows = []
    picam2.configure(config)
    picam2.start()

    try:
        for frame_index in range(args.warmup + args.frames):
            started = time.perf_counter()

            with picam2.captured_request() as request:
                # Materialise the main frame to include the full application path.
                request.make_array("main")
                outputs = imx500.get_outputs(request.get_metadata())

            elapsed_ms = (time.perf_counter() - started) * 1000

            if frame_index < args.warmup:
                continue

            detections = 0 if outputs is None else int(outputs[3][0])
            samples_ms.append(elapsed_ms)
            csv_rows.append((frame_index - args.warmup + 1, f"{elapsed_ms:.3f}", detections))
    finally:
        picam2.stop()

    mean_ms = statistics.mean(samples_ms)
    observed_fps = 1000 / mean_ms

    print("\n=== RESULTS ===")
    print(f"Mean pipeline cycle: {mean_ms:.2f} ms")
    print(f"Median pipeline cycle: {statistics.median(samples_ms):.2f} ms")
    print(f"P95 pipeline cycle: {percentile(samples_ms, 0.95):.2f} ms")
    print(f"Minimum pipeline cycle: {min(samples_ms):.2f} ms")
    print(f"Maximum pipeline cycle: {max(samples_ms):.2f} ms")
    print(f"Observed throughput: {observed_fps:.2f} FPS")
    print(
        "Note: this is end-to-end camera-to-output cycle time; it is not "
        "accelerator-only inference latency."
    )

    if args.csv:
        write_csv(args.csv, csv_rows)
        print(f"Per-frame timings written to: {args.csv}")


if __name__ == "__main__":
    main()
