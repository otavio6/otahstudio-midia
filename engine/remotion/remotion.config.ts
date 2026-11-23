import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(100);
Config.setCodec("h264");
Config.setCrf(14);
Config.setPixelFormat("yuv420p");
Config.setConcurrency(1);
Config.setColorSpace("bt709"); // trava o look: arquivo marcado como Rec.709, igual ao render local
Config.setOffthreadVideoCacheSizeInBytes(256 * 1024 * 1024); // VPS com pouca RAM: guarda no máximo 256 MB de quadros
