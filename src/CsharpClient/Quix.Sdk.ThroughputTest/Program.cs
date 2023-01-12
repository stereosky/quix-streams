﻿using System;
using System.Threading;
using Quix.Sdk.Speedtest;

namespace Quix.Sdk.ThroughputTest
{
    class Program
    {
        static void Main(string[] args)
        {
            var cts = new CancellationTokenSource();
            Console.CancelKeyPress += (s, e) =>
            {
                if (cts.IsCancellationRequested) return;
                Console.WriteLine("Cancelling....");
                e.Cancel = true;
                cts.Cancel();
            };
            
            
            new StreamingTest().Run(cts.Token);
        }
    }
}