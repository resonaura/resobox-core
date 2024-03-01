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

    PaStream *stream;
    // Открытие стандартного потока с одним входным и выходным каналом, с плавающей точкой, 44100 Гц, 256 фреймов на буфер и использованием нашей функции обратного вызова
    err = Pa_OpenDefaultStream(&stream,
                               1,          // Количество входных каналов
                               1,          // Количество выходных каналов
                               paFloat32,  // 32 бита с плавающей точкой
                               44100,      // Частота дискретизации
                               256,        // Фреймов на буфер
                               audioCallback,  // Функция обратного вызова
                               nullptr);   // Без пользовательских данных

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
