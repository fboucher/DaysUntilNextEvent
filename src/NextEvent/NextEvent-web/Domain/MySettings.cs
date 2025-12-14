using System;
using System.Diagnostics.CodeAnalysis;

namespace NextEvent_web.Domain;

public class MySettings
{
    public string ImportantDate { get; set; } = DateTime.Now.ToString("yyyy-MM-dd");
    public string StartFromDay { get; set; } = DateTime.Now.AddDays(-24).ToString("yyyy-MM-dd");

    public string PrimaryRGBColor { get; set; } = string.Empty;

    public string SecondaryRGBColor { get; set; } = string.Empty;

    public bool UseCustomColors { get; set; } = false;
    public string StartTime { get; set; } = "09:00";
    public string EndTime { get; set; } = "22:00";
    
    public bool FromPi { get; set; } = false;

    public bool IsReverse { get; set; } = false;

    public bool WithMarker { get; set; } = false;

    public string MarkerRGBColor { get; set; } = string.Empty;

    public bool IsFlashing { get; set; } = true;

    public int FlashSpeed { get; set; } = 2;

    public bool AutoUpdate { get; set; } = true;
}
