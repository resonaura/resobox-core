#include <iostream>
#include <portaudio.h>
#include <cmath> // Для использования sqrt() для расчета RMS

static int audioCallback(const void *inputBuffer, void *outputBuffer,
                         unsigned long framesPerBuffer,
                         const PaStreamCallbackTimeInfo* timeInfo,
                         PaStreamCallbackFlags statusFlags,
                         void *userData) {
    // Получаем данные о количестве входных каналов
    int inputChannelCount = 1;

    const float *in = (const float*)inputBuffer;
    float *out = (float*)outputBuffer;

    for(unsigned long i = 0; i < framesPerBuffer; ++i) {
        if (inputChannelCount == 1) {
            // Для моно входа копируем сэмпл в оба канала выхода
            float monoSample = *in++;
            *out++ = monoSample; // Левый канал
            *out++ = monoSample; // Правый канал
        } else if (inputChannelCount == 2) {
            // Для стерео входа копируем сэмплы напрямую
            *out++ = *in++; // Левый канал
            *out++ = *in++; // Правый канал
        }
    }

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
    inputParameters.channelCount = 1; // mono input
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
