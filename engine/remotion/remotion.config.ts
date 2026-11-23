import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setCodec("h264");
Config.setCrf(16);
Config.setPixelFormat("yuv420p");
Config.setConcurrency(1);
Config.setColorSpace("bt709"); // trava o look: arquivo marcado como Rec.709, igual ao render local
