#include <kfr/all.hpp>
#include <sndfile.h>
#include <vector>
#include <iostream>
#include <portaudio.h>
#include <cmath> // For using sqrt() for RMS calculations

// Correctly load an impulse response into a kfr::univector
kfr::univector<float> loadImpulseResponse(const std::string& filepath) {
    SF_INFO sfinfo;
    SNDFILE* file = sf_open(filepath.c_str(), SFM_READ, &sfinfo);
    if (!file) {
        std::cerr << "Error opening file: " << filepath << std::endl;
        return {};
    }

    if (sfinfo.channels > 1) {
        std::cerr << "Warning: Impulse response is not mono. Only the first channel will be used." << std::endl;
    }

    std::vector<float> buffer(sfinfo.frames);
    sf_count_t numFrames = sf_readf_float(file, buffer.data(), sfinfo.frames);

    if (numFrames < sfinfo.frames) {
        std::cerr << "Error reading file: " << filepath << std::endl;
        sf_close(file);
        return {};
    }

    sf_close(file);

    // Create a univector from the buffer
    return kfr::univector<float>(buffer.begin(), buffer.end());
}

// Initialize convolution engine correctly
auto impulseResponse = loadImpulseResponse("imp.wav");

static int audioCallback(const void *inputBuffer, void *outputBuffer,
                         unsigned long framesPerBuffer,
                         const PaStreamCallbackTimeInfo* timeInfo,
                         PaStreamCallbackFlags statusFlags,
                         void *userData) {
    auto* in = static_cast<const float*>(inputBuffer);
    auto* out = static_cast<float*>(outputBuffer);

    // Correct usage of univectors for input and output
    kfr::univector<float> input(in, in + framesPerBuffer);
    auto output = kfr::convolve(input, impulseResponse); // Adjust this line based on how you actually apply the convolution

    // Copy processed data to outputBuffer
    std::copy(output.begin(), output.end(), out);

    return paContinue;
}

int main() {
    PaError err = Pa_Initialize();
    if (err != paNoError) {
        std::cerr << "PortAudio error: " << Pa_GetErrorText(err) << std::endl;
        return 1;
    }

    int numDevices = Pa_GetDeviceCount();
    if (numDevices < 0) {
        printf("ERROR: Pa_CountDevices returned 0x%x\n", numDevices);
        err = numDevices;
    }

    printf("Number of devices = %d\n", numDevices);
    for (int i = 0; i < numDevices; i++) {
        const PaDeviceInfo *deviceInfo = Pa_GetDeviceInfo(i);
        printf("---------------------------------------\n");
        printf("Device #%d: %s\n", i, deviceInfo->name);
        printf("Max Input Channels: %d\n", deviceInfo->maxInputChannels);
        printf("Max Output Channels: %d\n", deviceInfo->maxOutputChannels);
        printf("Default Sample Rate: %f\n", deviceInfo->defaultSampleRate);
        // Add more device properties here as needed.
    }
    printf("---------------------------------------\n");


    PaStream *stream;

    PaStreamParameters inputParameters;
    inputParameters.device = 1; // or specify a device index
    inputParameters.channelCount = 2; // mono input
    inputParameters.sampleFormat = paFloat32; // 32-bit floating point input
    inputParameters.suggestedLatency = 0;
    inputParameters.hostApiSpecificStreamInfo = NULL;

    PaStreamParameters outputParameters;
    outputParameters.device = 1; // or specify a device index
    outputParameters.channelCount = 2; // stereo output
    outputParameters.sampleFormat = paFloat32; // 32-bit floating point output
    outputParameters.suggestedLatency = 0;
    outputParameters.hostApiSpecificStreamInfo = NULL;


    

    // Открытие стандартного потока с одним входным и выходным каналом, с плавающей точкой, 44100 Гц, 256 фреймов на буфер и использованием нашей функции обратного вызова
    err = Pa_OpenStream(&stream,
                               &inputParameters,          // Количество входных каналов
                               &outputParameters,          // Количество выходных каналов
                               44100,  // 32 бита с плавающей точкой
                               128,        // Фреймов на буфер
                               paClipOff,  // Функция обратного вызова
                               audioCallback, NULL);   // Без пользовательских данных

    if (err != paNoError) {
        std::cerr << "PortAudio error: " << Pa_GetErrorText(err) << std::endl;
        Pa_Terminate();
        return 1;
    }

    err = Pa_StartStream(stream);
    if (err != paNoError) {
        std::cerr << "PortAudio error: " << Pa_GetErrorText(err) << std::endl;
        Pa_CloseStream(stream);
        Pa_Terminate();
        return 1;
    }

    std::cout << "Press Enter to stop..." << std::endl;
    std::cin.get();

    err = Pa_StopStream(stream);
    if (err != paNoError) {
        std::cerr << "PortAudio error: " << Pa_GetErrorText(err) << std::endl;
    }

    Pa_CloseStream(stream);
    Pa_Terminate();

    return 0;
}
