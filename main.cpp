#include <iostream>
#include <portaudio.h>
#include <cmath> // Для использования sqrt() для расчета RMS

static int audioCallback(const void *inputBuffer, void *outputBuffer,
                         unsigned long framesPerBuffer,
                         const PaStreamCallbackTimeInfo* timeInfo,
                         PaStreamCallbackFlags statusFlags,
                         void *userData) {
    // Приведение типов входного и выходного буферов к float
    const float *in = (const float*)inputBuffer;
    float *out = (float*)outputBuffer;

    float sumSquares = 0.0; // Для накопления суммы квадратов сэмплов для расчета RMS

    // Простая пересылка данных и расчет RMS
    for (unsigned long i = 0; i < framesPerBuffer; i++) {
        *out++ = *in; // Пересылка данных
        
        // Расчет суммы квадратов для RMS
        sumSquares += (*in) * (*in);
        in++;
    }

    // Расчет и вывод RMS
    float rms = sqrt(sumSquares / framesPerBuffer);
    std::cout << "RMS: " << rms << std::endl;

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
    inputParameters.sampleFormat = paInt16; // 32-bit floating point input
    inputParameters.suggestedLatency = Pa_GetDeviceInfo(inputParameters.device)->defaultLowInputLatency;
    inputParameters.hostApiSpecificStreamInfo = NULL;

    PaStreamParameters outputParameters;
    outputParameters.device = 1; // or specify a device index
    outputParameters.channelCount = 2; // stereo output
    outputParameters.sampleFormat = paInt16; // 32-bit floating point output
    outputParameters.suggestedLatency = Pa_GetDeviceInfo(outputParameters.device)->defaultLowOutputLatency;
    outputParameters.hostApiSpecificStreamInfo = NULL;


    

    // Открытие стандартного потока с одним входным и выходным каналом, с плавающей точкой, 44100 Гц, 256 фреймов на буфер и использованием нашей функции обратного вызова
    err = Pa_OpenStream(&stream,
                               &inputParameters,          // Количество входных каналов
                               &outputParameters,          // Количество выходных каналов
                               44100,  // 32 бита с плавающей точкой
                               256,        // Фреймов на буфер
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
