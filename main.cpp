#include <iostream>
#include <portaudio.h>
#include <cmath> // Для использования sqrt() для расчета RMS
#include <math.h>

#define SAMPLE_RATE 44100  // Размер буфера дилея, 1 секунда при 44.1 кГц

static float delayBufferLeft[SAMPLE_RATE];
static float delayBufferRight[SAMPLE_RATE];
static int writeIndex = 0;  // Индекс записи для буфера дилея

// Глобальные переменные для фазера
const int PHASER_STAGES = 1024; // Количество стадий всепропускающих фильтров
float phaserBufferLeft[PHASER_STAGES] = {0};
float phaserBufferRight[PHASER_STAGES] = {0};
float lfoPhase = 0; // Фаза низкочастотного осциллятора

void applyPhaser(float &inLeft, float &inRight, float &outLeft, float &outRight, 
                 float rate, float depth, float feedback, float mix) {
    // Обновляем фазу LFO
    lfoPhase += rate;
    if (lfoPhase > 1.0f) lfoPhase -= 1.0f;

    // Вычисляем модулированное смещение для фазы
    float lfo = (1 + cos(2 * M_PI * lfoPhase)) / 2; // LFO в диапазоне [0,1]
    float modulatedDepth = lfo * depth;

    // Входной сигнал с добавлением обратной связи
    float processedLeft = inLeft + phaserBufferLeft[PHASER_STAGES - 1] * feedback;
    float processedRight = inRight + phaserBufferRight[PHASER_STAGES - 1] * feedback;

    // Проход через цепочку всепропускающих фильтров
    for (int i = 0; i < PHASER_STAGES; ++i) {
        float oldLeft = phaserBufferLeft[i];
        float oldRight = phaserBufferRight[i];

        phaserBufferLeft[i] = processedLeft + oldLeft * modulatedDepth;
        phaserBufferRight[i] = processedRight + oldRight * modulatedDepth;

        processedLeft = oldLeft - phaserBufferLeft[i] * modulatedDepth;
        processedRight = oldRight - phaserBufferRight[i] * modulatedDepth;
    }

    // Смешиваем обработанный сигнал с оригинальным
    outLeft = mix * processedLeft + (1 - mix) * inLeft;
    outRight = mix * processedRight + (1 - mix) * inRight;
}

void applyDelay(float &inLeft, float &inRight, float &outLeft, float &outRight, float delayTimeMs, float feedback, float mix) {
    int readIndex = (writeIndex - static_cast<int>(delayTimeMs * 44.1)) % SAMPLE_RATE;  // Вычисляем индекс чтения
    if (readIndex < 0) {
        readIndex += SAMPLE_RATE;  // Убедимся, что индекс чтения положительный
    }

    // Применяем дилей
    float processedSampleLeft = delayBufferLeft[readIndex];
    float processedSampleRight = delayBufferRight[readIndex];

    outLeft = inLeft * (1 - mix) + processedSampleLeft * mix;
    outRight = inRight * (1 - mix) + processedSampleRight * mix;

    // Записываем семплы в буфер дилея
    delayBufferLeft[writeIndex] = outLeft * feedback;
    delayBufferRight[writeIndex] = outRight * feedback;

    // Инкрементируем индекс записи
    writeIndex = (writeIndex + 1) % SAMPLE_RATE;
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
        float inLeft, inRight, doutLeft, doutRight, outLeft, outRight;

        // Чтение входных семплов
        inLeft = *in++;
        if (inputChannelCount == 2) {
            inRight = *in++;
        } else {
            inRight = inLeft;  // Для моно сигнала копируем левый канал в правый
        }

        // Применяем дилей
        applyDelay(inLeft, inRight, doutLeft, doutRight, 500, 0.5, 0.5);
        applyPhaser(doutLeft, doutRight, outLeft, outRight, 1, 0.7, 0.15, .5);

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
