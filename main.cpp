#include <iostream>
#include <portaudio.h>
#include <cmath> // Для использования sqrt() для расчета RMS

#define DELAY_BUFFER_SIZE 44100  // Размер буфера дилея, 1 секунда при 44.1 кГц

static float delayBufferLeft[DELAY_BUFFER_SIZE];
static float delayBufferRight[DELAY_BUFFER_SIZE];
static int writeIndex = 0;  // Индекс записи для буфера дилея

void applyDelay(float &inLeft, float &inRight, float &outLeft, float &outRight, float delayTimeMs, float feedback) {
    int readIndex = (writeIndex - static_cast<int>(delayTimeMs * 44.1)) % DELAY_BUFFER_SIZE;  // Вычисляем индекс чтения
    if (readIndex < 0) {
        readIndex += DELAY_BUFFER_SIZE;  // Убедимся, что индекс чтения положительный
    }

    // Применяем дилей
    outLeft = delayBufferLeft[readIndex] + inLeft;
    outRight = delayBufferRight[readIndex] + inRight;

    // Записываем семплы в буфер дилея
    delayBufferLeft[writeIndex] = outLeft * feedback;
    delayBufferRight[writeIndex] = outRight * feedback;

    // Инкрементируем индекс записи
    writeIndex = (writeIndex + 1) % DELAY_BUFFER_SIZE;
}

static int audioCallback(const void *inputBuffer, void *outputBuffer,
                         unsigned long framesPerBuffer,
                         const PaStreamCallbackTimeInfo* timeInfo,
                         PaStreamCallbackFlags statusFlags,
                         void *userData) {
    int inputChannelCount = 1;

    const float *in = (const float*)inputBuffer;
    float *out = (float*)outputBuffer;

    for(unsigned long i = 0; i < framesPerBuffer; ++i) {
        float inLeft, inRight, outLeft, outRight;

        // Чтение входных семплов
        inLeft = *in++;
        if (inputChannelCount == 2) {
            inRight = *in++;
        } else {
            inRight = inLeft;  // Для моно сигнала копируем левый канал в правый
        }

        // Применяем дилей
        applyDelay(inLeft, inRight, outLeft, outRight, 500, 0.5);

        // Записываем семплы в выходной буфер
        *out++ = outLeft;
        *out++ = outRight;
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
    inputParameters.device = 3; // or specify a device index
    inputParameters.channelCount = 1; // mono input
    inputParameters.sampleFormat = paFloat32; // 32-bit floating point input
    inputParameters.suggestedLatency = 0;
    inputParameters.hostApiSpecificStreamInfo = NULL;

    PaStreamParameters outputParameters;
    outputParameters.device = 2; // or specify a device index
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
